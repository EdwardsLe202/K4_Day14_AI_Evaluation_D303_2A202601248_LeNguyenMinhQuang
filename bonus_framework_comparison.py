"""Run the Exercise 3.4 RAGAS vs. DeepEval comparison.

Both frameworks evaluate the same saved OpenRouter answers and retrieved
contexts with the same OpenRouter judge.  Results are checkpointed after every
case so an interrupted run can be resumed safely.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from statistics import mean
from typing import Any, Awaitable, Callable, TypeVar

from deepeval.metrics import FaithfulnessMetric, GEval
from deepeval.metrics.g_eval.utils import Rubric
from deepeval.models import OpenRouterModel
from deepeval.test_case import LLMTestCase, SingleTurnParams
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerAccuracy, Faithfulness


DEFAULT_DATASET = Path("golden_dataset.json")
DEFAULT_ANSWERS = Path("artifacts/actual_answers.json")
DEFAULT_OUTPUT = Path("artifacts/framework_comparison.json")
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
PASS_THRESHOLD = 0.5

T = TypeVar("T")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--ids",
        nargs="*",
        help="Optional case IDs to evaluate; the default is all matched cases.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Discard checkpointed scores and evaluate selected cases again.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Attempts per framework/case after framework-internal retries.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def build_cases(
    dataset: dict[str, Any], answers: dict[str, Any]
) -> list[dict[str, Any]]:
    gold_by_id = {row["id"]: row for row in dataset["qa_pairs"]}
    answer_by_id = {row["id"]: row for row in answers["answers"]}
    if set(gold_by_id) != set(answer_by_id):
        missing_answers = sorted(set(gold_by_id) - set(answer_by_id))
        extra_answers = sorted(set(answer_by_id) - set(gold_by_id))
        raise ValueError(
            "Dataset/answer IDs differ: "
            f"missing_answers={missing_answers}, extra_answers={extra_answers}"
        )

    cases: list[dict[str, Any]] = []
    for case_id, gold in gold_by_id.items():
        answer = answer_by_id[case_id]
        if gold["question"] != answer["question"]:
            raise ValueError(f"Question mismatch for {case_id}")
        if answer.get("error"):
            raise ValueError(f"Saved answer {case_id} has an error: {answer['error']}")

        contexts = [item["text"] for item in answer["retrieved_contexts"]]
        if not contexts:
            raise ValueError(f"Saved answer {case_id} has no retrieved contexts")
        cases.append(
            {
                "id": case_id,
                "difficulty": gold["difficulty"],
                "question": gold["question"],
                "reference": gold["expected_answer"],
                "response": answer["actual_answer"],
                "retrieved_contexts": contexts,
            }
        )
    return cases


async def with_retries(
    operation: Callable[[], Awaitable[T]], attempts: int, label: str
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except Exception as error:  # Preserve final failure in the artifact.
            last_error = error
            if attempt < attempts:
                delay = 2**attempt
                print(
                    f"  retry {attempt}/{attempts - 1} for {label}: "
                    f"{type(error).__name__}",
                    flush=True,
                )
                await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


def score_record(faithfulness: float, answer_quality: float) -> dict[str, Any]:
    if not all(math.isfinite(value) for value in (faithfulness, answer_quality)):
        raise ValueError("Framework returned a non-finite score")
    overall = mean((faithfulness, answer_quality))
    return {
        "faithfulness": faithfulness,
        "answer_quality": answer_quality,
        "overall": overall,
        "passed": faithfulness >= PASS_THRESHOLD
        and answer_quality >= PASS_THRESHOLD,
    }


async def evaluate_ragas(
    case: dict[str, Any], faithfulness: Faithfulness, accuracy: AnswerAccuracy
) -> dict[str, Any]:
    faith_result, accuracy_result = await asyncio.gather(
        faithfulness.ascore(
            user_input=case["question"],
            response=case["response"],
            retrieved_contexts=case["retrieved_contexts"],
        ),
        accuracy.ascore(
            user_input=case["question"],
            response=case["response"],
            reference=case["reference"],
        ),
    )
    return score_record(float(faith_result.value), float(accuracy_result.value))


def build_deepeval_metrics(
    judge: OpenRouterModel,
) -> tuple[FaithfulnessMetric, GEval]:
    faithfulness = FaithfulnessMetric(
        threshold=PASS_THRESHOLD,
        model=judge,
        include_reason=False,
        async_mode=True,
    )
    accuracy = GEval(
        name="Reference Answer Quality",
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        evaluation_steps=[
            "Compare the factual claims in Actual Output with Expected Output for the Input.",
            "Check whether all decision-changing dates, amounts, conditions, exceptions, and requested next steps are present.",
            "Penalize contradictions, unsupported entitlements, privacy violations, and unsafe instructions more heavily than minor omissions.",
            "Assign only 0 for materially wrong or unsafe, 5 for partially correct with an important omission, or 10 for fully correct with at most a non-decision-changing omission.",
        ],
        rubric=[
            Rubric(
                score_range=(0, 0),
                expected_outcome="Materially wrong, irrelevant, unsafe, or contradicts the reference.",
            ),
            Rubric(
                score_range=(5, 5),
                expected_outcome="Partially correct but misses an important condition, exception, amount, date, or requested subpart.",
            ),
            Rubric(
                score_range=(10, 10),
                expected_outcome="Fully correct; any omission cannot change the user's decision or next action.",
            ),
        ],
        model=judge,
        threshold=PASS_THRESHOLD,
        async_mode=True,
    )
    return faithfulness, accuracy


async def evaluate_deepeval(
    case: dict[str, Any], judge: OpenRouterModel
) -> dict[str, Any]:
    faithfulness, accuracy = build_deepeval_metrics(judge)
    test_case = LLMTestCase(
        input=case["question"],
        actual_output=case["response"],
        expected_output=case["reference"],
        retrieval_context=case["retrieved_contexts"],
    )
    faith_score, accuracy_score = await asyncio.gather(
        faithfulness.a_measure(test_case, _show_indicator=False),
        accuracy.a_measure(test_case, _show_indicator=False),
    )
    result = score_record(float(faith_score), float(accuracy_score))
    result["answer_quality_reason"] = accuracy.reason
    return result


def average_ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average_rank = (index + 1 + end) / 2
        for position in range(index, end):
            ranks[ordered[position][0]] = average_rank
        index = end
    return ranks


def pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    left_mean, right_mean = mean(left), mean(right)
    numerator = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left, right)
    )
    left_sum = sum((x - left_mean) ** 2 for x in left)
    right_sum = sum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_sum * right_sum)
    return numerator / denominator if denominator else None


def cohen_kappa(left: list[bool], right: list[bool]) -> float | None:
    if not left or len(left) != len(right):
        return None
    observed = mean(a == b for a, b in zip(left, right))
    left_positive = mean(left)
    right_positive = mean(right)
    expected = left_positive * right_positive + (1 - left_positive) * (
        1 - right_positive
    )
    return (observed - expected) / (1 - expected) if expected != 1 else None


def framework_summary(rows: list[dict[str, Any]], framework: str) -> dict[str, Any]:
    scores = [row[framework] for row in rows]
    passed = sum(score["passed"] for score in scores)
    return {
        "evaluated": len(scores),
        "mean_faithfulness": mean(score["faithfulness"] for score in scores),
        "mean_answer_quality": mean(score["answer_quality"] for score in scores),
        "mean_overall": mean(score["overall"] for score in scores),
        "passed": passed,
        "pass_rate": passed / len(scores),
        "failed_ids": [row["id"] for row in rows if not row[framework]["passed"]],
        "bottom_3_cases": [
            {"id": row["id"], "overall": row[framework]["overall"]}
            for row in sorted(rows, key=lambda item: item[framework]["overall"])[:3]
        ],
    }


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    complete = [
        row
        for row in results
        if "error" not in row.get("ragas", {})
        and "error" not in row.get("deepeval", {})
        and "overall" in row.get("ragas", {})
        and "overall" in row.get("deepeval", {})
    ]
    if not complete:
        return {"complete_cases": 0}

    ragas_overall = [row["ragas"]["overall"] for row in complete]
    deepeval_overall = [row["deepeval"]["overall"] for row in complete]
    ragas_pass = [row["ragas"]["passed"] for row in complete]
    deepeval_pass = [row["deepeval"]["passed"] for row in complete]
    ragas_summary = framework_summary(complete, "ragas")
    deepeval_summary = framework_summary(complete, "deepeval")
    ragas_bottom = {row["id"] for row in ragas_summary["bottom_3_cases"]}
    deepeval_bottom = {row["id"] for row in deepeval_summary["bottom_3_cases"]}

    if ragas_summary["mean_overall"] < deepeval_summary["mean_overall"]:
        lower_scoring = "ragas"
    elif deepeval_summary["mean_overall"] < ragas_summary["mean_overall"]:
        lower_scoring = "deepeval"
    else:
        lower_scoring = "tie"

    return {
        "complete_cases": len(complete),
        "ragas": ragas_summary,
        "deepeval": deepeval_summary,
        "comparison": {
            "spearman_overall": pearson(
                average_ranks(ragas_overall), average_ranks(deepeval_overall)
            ),
            "pass_fail_agreement": mean(
                a == b for a, b in zip(ragas_pass, deepeval_pass)
            ),
            "cohen_kappa": cohen_kappa(ragas_pass, deepeval_pass),
            "mean_absolute_overall_gap": mean(
                abs(a - b) for a, b in zip(ragas_overall, deepeval_overall)
            ),
            "bottom_3_overlap": sorted(ragas_bottom & deepeval_bottom),
            "lower_mean_overall": lower_scoring,
        },
    }


def write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    artifact["generated_at"] = datetime.now(timezone.utc).isoformat()
    artifact["summary"] = build_summary(artifact["results"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def make_artifact(
    model: str,
    cases: list[dict[str, Any]],
    dataset_path: Path,
    answers_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "protocol": {
            "dataset": str(dataset_path),
            "dataset_sha256": sha256_file(dataset_path),
            "answers": str(answers_path),
            "answers_sha256": sha256_file(answers_path),
            "case_count": len(cases),
            "judge_provider": "OpenRouter",
            "judge_model": model,
            "temperature": 0,
            "pass_threshold": PASS_THRESHOLD,
            "pass_rule": "faithfulness >= 0.5 AND answer_quality >= 0.5",
            "overall_formula": "mean(faithfulness, answer_quality)",
            "ragas_metrics": ["Faithfulness", "AnswerAccuracy"],
            "deepeval_metrics": ["FaithfulnessMetric", "GEval reference answer quality"],
            "framework_versions": {
                "ragas": version("ragas"),
                "deepeval": version("deepeval"),
            },
            "python": platform.python_version(),
        },
        "generated_at": None,
        "summary": {"complete_cases": 0},
        "results": [],
    }


async def run(args: argparse.Namespace) -> int:
    load_dotenv(".env")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required in the environment or .env")
    model_name = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL)

    dataset = load_json(args.dataset)
    answers = load_json(args.answers)
    all_cases = build_cases(dataset, answers)
    cases = all_cases
    if args.ids:
        selected = set(args.ids)
        unknown = selected - {case["id"] for case in cases}
        if unknown:
            raise ValueError(f"Unknown case IDs: {sorted(unknown)}")
        cases = [case for case in cases if case["id"] in selected]

    if args.force or not args.output.exists():
        artifact = make_artifact(
            model_name, cases, args.dataset, args.answers
        )
    else:
        artifact = load_json(args.output)
        protocol = artifact.get("protocol", {})
        if protocol.get("judge_model") != model_name:
            raise ValueError("Checkpoint judge model differs; use --force to replace it")
        expected_hashes = {
            "dataset_sha256": sha256_file(args.dataset),
            "answers_sha256": sha256_file(args.answers),
        }
        for field, expected in expected_hashes.items():
            actual = protocol.get(field)
            if actual is not None and actual != expected:
                raise ValueError(
                    f"Checkpoint {field} differs; use --force to replace it"
                )
        protocol.update(
            {
                "dataset": str(args.dataset),
                "answers": str(args.answers),
                **expected_hashes,
            }
        )

    rows_by_id = {row["id"]: row for row in artifact.get("results", [])}
    openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    ragas_llm = llm_factory(model_name, provider="openai", client=openai_client)
    ragas_faithfulness = Faithfulness(llm=ragas_llm)
    ragas_accuracy = AnswerAccuracy(llm=ragas_llm)
    deepeval_judge = OpenRouterModel(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
    )

    for index, case in enumerate(cases, start=1):
        case_id = case["id"]
        row = rows_by_id.setdefault(
            case_id, {"id": case_id, "difficulty": case["difficulty"]}
        )
        print(f"[{index}/{len(cases)}] {case_id}", flush=True)

        if args.force or "overall" not in row.get("ragas", {}):
            try:
                row["ragas"] = await with_retries(
                    lambda: evaluate_ragas(
                        case, ragas_faithfulness, ragas_accuracy
                    ),
                    args.retries,
                    f"RAGAS/{case_id}",
                )
                print(
                    f"  RAGAS overall={row['ragas']['overall']:.3f} "
                    f"pass={row['ragas']['passed']}",
                    flush=True,
                )
            except Exception as error:
                row["ragas"] = {
                    "error": f"{type(error).__name__}: {error}"
                }
                print(f"  RAGAS ERROR: {type(error).__name__}: {error}", flush=True)

        if args.force or "overall" not in row.get("deepeval", {}):
            try:
                row["deepeval"] = await with_retries(
                    lambda: evaluate_deepeval(case, deepeval_judge),
                    args.retries,
                    f"DeepEval/{case_id}",
                )
                print(
                    f"  DeepEval overall={row['deepeval']['overall']:.3f} "
                    f"pass={row['deepeval']['passed']}",
                    flush=True,
                )
            except Exception as error:
                row["deepeval"] = {
                    "error": f"{type(error).__name__}: {error}"
                }
                print(
                    f"  DeepEval ERROR: {type(error).__name__}: {error}",
                    flush=True,
                )

        artifact["results"] = [
            rows_by_id[item["id"]]
            for item in all_cases
            if item["id"] in rows_by_id
        ]
        write_artifact(args.output, artifact)

    selected_ids = {case["id"] for case in cases}
    selected_complete = sum(
        row["id"] in selected_ids
        and "overall" in row.get("ragas", {})
        and "overall" in row.get("deepeval", {})
        for row in artifact["results"]
    )
    print(
        f"Saved {selected_complete}/{len(cases)} selected complete cases "
        f"to {args.output}",
        flush=True,
    )
    await openai_client.close()
    return 0 if selected_complete == len(cases) else 1


def main() -> int:
    args = parse_args()
    if args.retries < 1:
        raise ValueError("--retries must be at least 1")
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
