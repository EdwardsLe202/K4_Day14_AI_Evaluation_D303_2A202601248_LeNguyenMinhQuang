"""Generate a reproducible offline RAG baseline when no API key is available.

This script uses the provided DomainAssistant and BM25 retriever unchanged. Its
extractive generator sees only the question and retrieved chunks in the prompt;
it never reads golden expected answers or gold contexts.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from domain_assistant import _tokenize, generate_actual_answers


class OfflineExtractiveGenerator:
    """Select the most question-relevant sentences from retrieved chunks."""

    model = "offline-extractive-v1"

    def generate(self, prompt: str) -> str:
        question_match = re.search(
            r"Question:\n(?P<question>.*?)\n\nRetrieved contexts:\n",
            prompt,
            flags=re.DOTALL,
        )
        context_match = re.search(
            r"Retrieved contexts:\n(?P<contexts>.*?)\n\nAnswer:",
            prompt,
            flags=re.DOTALL,
        )
        if question_match is None or context_match is None:
            raise ValueError("Unexpected DomainAssistant prompt format")

        question_tokens = set(_tokenize(question_match.group("question")))
        context_text = re.sub(
            r"\[Context \d+ \| [^\]]+\]\n",
            "",
            context_match.group("contexts"),
        )
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", context_text)
            if sentence.strip()
        ]

        ranked: list[tuple[float, int, str]] = []
        for index, sentence in enumerate(sentences):
            sentence_tokens = set(_tokenize(sentence))
            overlap = len(question_tokens & sentence_tokens)
            if not overlap:
                continue
            query_coverage = overlap / max(1, len(question_tokens))
            sentence_density = overlap / max(1, len(sentence_tokens))
            ranked.append((query_coverage + sentence_density, index, sentence))

        selected = sorted(ranked, key=lambda item: (-item[0], item[1]))[:6]
        if not selected:
            return "The retrieved contexts do not provide enough information to answer this question."
        selected.sort(key=lambda item: item[1])
        return " ".join(sentence for _, _, sentence in selected)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("golden_dataset.json"))
    parser.add_argument(
        "--corpus-dir", type=Path, default=Path("data/technology_store")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/actual_answers.json")
    )
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact = generate_actual_answers(
        dataset_path=args.dataset,
        corpus_dir=args.corpus_dir,
        generator=OfflineExtractiveGenerator(),
        top_k=args.top_k,
        progress=print,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved actual answers: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
