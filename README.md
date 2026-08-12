# Ngày 14 — AI Evaluation & Benchmarking Pipeline

**AICB-P1 · Phase 1 · Ngày 14 trong 15 · K4**

Lab này là bài **AI Evaluation**. Bạn sẽ hoàn thiện evaluation core trong
`template.py`, xây dựng một golden dataset 20 câu, chạy một hệ thống RAG thật
trên corpus **OrbitTech Store Customer Support**, rồi phân tích kết quả.

> Hệ thống RAG trong `domain_assistant.py` là **system under evaluation**. Nó
> sinh câu trả lời; `template.py` là **evaluation engine** chấm các câu trả lời
> đó. Hai phần có vai trò khác nhau.

Hướng dẫn thao tác đầy đủ nằm trong [`guide_lab.md`](guide_lab.md).

---

## Yêu cầu & Quick Start

**Yêu cầu:** Python 3.11 trở lên. Cần **OpenRouter hoặc OpenAI API key** để
chạy `domain_assistant.py` (Part 3 — sinh 20 actual answers từ RAG thật); phần
code core (`template.py`, Part 1–2) không cần API key.

```bash
python --version                        # xác nhận 3.11+
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pytest tests/ -v                         # baseline: 42 tests collected, 42 failed
cp .env.example .env                     # rồi điền OpenRouter/OpenAI key cho Part 3
```

Chi tiết đầy đủ theo hệ điều hành, xử lý lỗi thường gặp: xem [`guide_lab.md`](guide_lab.md) Mục 2 và Mục 15.

---

## Mục tiêu

Sau lab này, bạn sẽ:

1. Xây dựng pipeline đánh giá tự động cho AI agent trên 20 test cases.
2. Triển khai các metrics lấy cảm hứng từ RAGAS, gồm answer-side và retrieval-side.
3. Thiết kế LLM-as-a-Judge rubric theo thang điểm 1–5 và nhận diện bias.
4. Xây dựng golden dataset bằng stratified sampling.
5. Thực hiện failure analysis bằng failure clustering và 5 Whys.
6. Hiểu cách dùng evaluation như một CI/CD quality gate.

---

## Luồng end-to-end của bài lab

```text
data/technology_store/*.md
             │
             ├── học viên đọc và viết ──> golden_dataset.json
             │                               │
             └── DomainAssistant <── question
                       │
                       ├── retrieve chunks
                       └── generate actual answer
                                  │
                                  v
                     artifacts/actual_answers.json
                                  │
                    evaluate_answers.py
                                  │
                 template.py (evaluation core)
                                  │
                                  v
                  artifacts/benchmark_results.json
                                  │
                     exercises.md + reflection.md
```

`domain_assistant.py` chỉ đọc `id` và `question` khi sinh answer. Nó **không
đọc `expected_answer` hoặc gold contexts để trả lời**, vì làm vậy sẽ gây data
leakage và làm benchmark mất ý nghĩa.

---

## Bối cảnh lý thuyết

### Evaluation = Scientific Method cho AI

```text
Hypothesis → Experiment → Measure → Conclude → Iterate
```

Evaluation tốt phải **lặp lại được**, **so sánh được** và **chạy tự động được**.

### Ba loại evaluation

| Loại | Khi nào | Ví dụ công cụ |
|---|---|---|
| Offline | Mỗi release hoặc prompt change | RAGAS, DeepEval, TruLens |
| Online | Continuous, real traffic | TruLens, Langfuse |
| Human | High-stakes hoặc cần calibration | Annotation UI, spreadsheet |

### Bốn nhóm metrics

| Nhóm | Metrics |
|---|---|
| Task Completion | Binary pass/fail, partial credit |
| Answer Quality | Accuracy, completeness, coherence |
| RAG-Specific | Faithfulness, relevance, context recall, context precision |
| Business | User satisfaction, time saved, cost, adoption |

### RAG metrics pipeline

```text
Question → Retriever → Context → Generator → Answer
              ↓            ↓          ↓           ↓
         Context       Context   Faithfulness  Answer
          Recall      Precision                Relevance
```

| Metric | Câu hỏi cần trả lời | Heuristic trong lab |
|---|---|---|
| Faithfulness | Answer có grounded trong gold context không? | `|answer ∩ context| / |answer|` |
| Relevance | Answer có trả lời đúng question không? | `|answer ∩ question| / |question|` |
| Completeness | Answer có đủ nội dung expected không? | `|answer ∩ expected| / |expected|` |
| Context Recall | Retriever có lấy đủ evidence không? | `|expected ∩ union(chunks)| / |expected|` |
| Context Precision | Chunk relevant có đứng sớm trong ranking không? | Average Precision@K |

Hai retrieval metrics chạy trên `QAPair.retrieved_contexts`, là danh sách
chunks theo đúng thứ tự retriever trả về. Chúng dùng để chẩn đoán retrieval và
không được đưa vào `overall_score()` của core gốc.

### LLM-as-a-Judge

Judge nhận question, agent answer và rubric, sau đó trả score cùng rationale.
Rubric cần mô tả rõ từng mức 1–5. Các bias cần lưu ý:

- Position bias: ưu tiên answer xuất hiện trước.
- Verbosity bias: ưu tiên answer dài.
- Self-preference bias: ưu tiên output giống model judge.

Best practices gồm randomize order, multiple judges và calibration với human.

### Golden Dataset Design

| Phân bổ | Mục đích |
|---|---|
| 5 Easy | Factual lookup, thường dùng một document |
| 7 Medium | Kết hợp quy trình hoặc evidence từ 2–3 documents |
| 5 Hard | Nhiều điều kiện, ngoại lệ, effective date hoặc ambiguity |
| 3 Adversarial | Out-of-scope, prompt injection, false premise/trap |

### Failure taxonomy

| Loại | Triệu chứng | Root cause thường gặp |
|---|---|---|
| `hallucination` | Answer không grounded | Context hoặc grounding guardrail yếu |
| `irrelevant` | Không giải quyết question | Prompt/routing sai |
| `incomplete` | Bỏ sót thông tin quan trọng | Retrieval thiếu hoặc generation thiếu |
| `off_topic` | Trả lời sai chủ đề | Intent detection sai |
| `refusal` | Từ chối khi nên trả lời | Guardrail quá chặt |

### Evaluation frameworks

| Framework | Focus | Phù hợp nhất với |
|---|---|---|
| RAGAS | RAG metrics chuẩn hóa | RAG offline evaluation |
| DeepEval | LLM unit testing, pytest-native | CI/CD assertions |
| TruLens | Feedback functions và tracing | Online + offline monitoring |

---

## Cấu trúc repo

```text
.
├── data/technology_store/       # corpus nguồn được cung cấp
├── solution/                    # nơi nộp solution.py hoàn chỉnh
├── tests/                       # test suite của evaluation core
├── README.md                    # đề bài, deliverables và rubric
├── guide_lab.md                 # hướng dẫn từng bước end-to-end
├── exercises.md                 # worksheet Part 1–3
├── reflection.md                # evaluation report và failure analysis
├── template.py                  # starter evaluation core có TODO
├── domain_assistant.py          # RAG system under evaluation
├── evaluate_answers.py          # adapter artifact → evaluation core
├── validate_golden_dataset.py   # kiểm tra schema và evidence
├── golden_dataset.json          # form 20 QA để học viên điền
├── requirements.txt
└── .env.example
```

Sau khi chạy RAG và benchmark, scripts tự tạo:

```text
artifacts/
├── actual_answers.json
└── benchmark_results.json
```

Hai artifact giúp bạn kiểm tra và phân tích quá trình chạy. Chúng không phải
deliverable bắt buộc và không được chấm theo việc có commit hay không.

---

## Tasks

### Task 1 — Data Models

Hoàn thiện `QAPair`, `EvalResult` và `overall_score()` trong `template.py`.

### Task 2 — RAGASEvaluator

Triển khai ba answer-side metrics:

- `evaluate_faithfulness`
- `evaluate_relevance`
- `evaluate_completeness`

Triển khai hai retrieval-side metrics:

- `evaluate_context_recall`
- `evaluate_context_precision`

`run_full_eval(..., contexts=None)` phải luôn chạy ba answer metrics. Khi có
`contexts`, hàm tính thêm hai retrieval metrics và lưu vào `EvalResult`.

### Task 3 — LLMJudge

- `score_response`: build judge prompt, gọi judge function và parse scores.
- `detect_bias`: phát hiện positional, leniency và severity bias.

### Task 4 — BenchmarkRunner

- `run`: chạy mọi QA qua `agent_fn` và evaluator.
- `generate_report`: tổng hợp pass rate và trung bình metrics.
- `run_regression`: phát hiện metric giảm quá 0.05.
- `identify_failures`: lọc cases dưới threshold.

Trong `run`, phải truyền `pair.retrieved_contexts` vào optional `contexts` của
`run_full_eval`. Trong report, tính thêm average Context Recall và Context
Precision trên những result có retrieval scores.

### Task 5 — FailureAnalyzer

- `categorize_failures`
- `find_root_cause`
- `generate_improvement_suggestions`
- `generate_improvement_log`

### Task 6 — Golden Dataset và benchmark thật

1. Điền 20 QA trong `golden_dataset.json`.
2. Validate schema, distribution, coverage và evidence provenance.
3. Chạy RAG để tạo 20 actual answers.
4. Chạy core evaluation và ghi kết quả vào `exercises.md`.
5. Phân tích ba failures tệ nhất trong `reflection.md`.

---

## Sản phẩm nộp bài

| File | Yêu cầu |
|---|---|
| `solution/solution.py` | Hoàn thiện tất cả TODO bắt buộc của evaluation core |
| `golden_dataset.json` | Đủ 20 QA, đúng schema, distribution và evidence |
| `exercises.md` | Hoàn thành worksheet, benchmark 3.2 và rubric 3.3 |
| `reflection.md` | Evaluation report, 3 failures, 5 Whys và regression strategy |

---

## Thời gian làm bài

Buổi học diễn ra từ **14:15 đến 18:00**. Hoàn thành bài lab trước **17:00**;
thời gian 17:00–18:00 dành cho demo và Q&A.

| Thời gian | Hoạt động |
|---|---|
| 14:15–14:30 | Tạo môi trường, smoke test và baseline tests |
| 14:30–14:45 | Part 1 — Warm-up |
| 14:45–15:40 | Part 2 — Core Coding và checkpoint tests |
| 15:40–16:35 | Part 3 — Golden Dataset, RAG, benchmark và rubric |
| 16:35–16:50 | Part 4 — Failure analysis và reflection |
| 16:50–17:00 | Copy solution, chạy kiểm tra cuối và rà deliverables |
| 17:00–18:00 | Demo và Q&A |

---

## Rubric

| Tiêu chí | Điểm |
|---|---:|
| Core coding hoàn chỉnh, toàn bộ required tests pass | 50 |
| Golden dataset 20 QA đúng schema, stratification và evidence | 15 |
| LLM-as-a-Judge rubric design rõ ràng, domain-specific | 10 |
| Benchmark, 5 Whys, failure analysis và improvement log | 15 |
| Chất lượng code, type hints và regression strategy | 10 |
| **Tổng** | **100** |

Bonus không thay thế phần điểm bắt buộc:

| Bonus | Điểm tối đa |
|---|---:|
| Exercise 3.4 — so sánh hai evaluation frameworks | +10 |
| Exercise 3.5 — reranking và phân tích retrieval metrics | +5 |

> **Benchmark score không quyết định điểm lab.** LLM output có thể thay đổi theo
> model và từng lần chạy. Điểm được chấm dựa trên pipeline đúng, dataset có chất
> lượng, evidence hợp lệ và phân tích có căn cứ — không dựa trên việc pass rate
> phải đạt một con số cố định.

---

## Checklist trước khi nộp

- [ ] `python validate_golden_dataset.py` báo `PASS`.
- [ ] Toàn bộ required tests pass.
- [ ] `golden_dataset.json` đủ 5 Easy + 7 Medium + 5 Hard + 3 Adversarial.
- [ ] Đã kiểm tra `artifacts/actual_answers.json` sau khi chạy RAG.
- [ ] Exercise 3.2 có đủ năm metrics và ba cases thấp nhất.
- [ ] Exercise 3.3 có rubric 1–5 và edge cases.
- [ ] `reflection.md` có ba 5 Whys analyses và improvement log.
- [ ] `solution/solution.py` là bản hoàn thiện của `template.py`.
- [ ] Không commit `.env`, API key hoặc dữ liệu giảng viên cung cấp ngoài repo.
