# Guide Lab — AI Evaluation End to End

Tài liệu này hướng dẫn toàn bộ workflow của lab K4, từ tạo repo cá nhân đến
chạy RAG, benchmark và hoàn thiện bài nộp. Làm theo thứ tự; không gọi API trước
khi golden dataset validate thành công.

---

## 0. Hiểu đúng ba thành phần

### Thành phần 1 — System under evaluation

`domain_assistant.py` là RAG assistant cho OrbitTech Store Customer Support:

```text
question → BM25 retrieval → retrieved chunks → OpenAI model → actual answer
```

Đây là thành phần **sinh câu trả lời thật**.

### Thành phần 2 — Evaluation core

`template.py` chứa data models, metrics, benchmark runner, LLM judge và failure
analyzer. Học viên hoàn thiện TODO trong file này.

Demo `mock_agent` ở cuối `template.py` chỉ giúp kiểm tra core bằng dữ liệu nhỏ.
Nó không thay thế `domain_assistant.py` và không tạo 20 actual answers của bài.

### Thành phần 3 — Artifact adapter

`evaluate_answers.py` đọc golden dataset và actual answers đã lưu, sau đó đưa
chúng vào `BenchmarkRunner` và `RAGASEvaluator` trong `template.py`.

Nó chỉ làm I/O và format Exercise 3.2; nó không viết lại evaluation metrics.

---

## 1. Tạo repo cá nhân

Lab làm **cá nhân**. Tên repo:

```text
K4_Day14_AI_Evaluation_<Phong>_<MaSoSinhVien>_<HoVaTenKhongDauCach>
```

Ví dụ:

```text
K4_Day14_AI_Evaluation_D305_2A20260XXX_NguyenVanA
```

### Cách A — Fork repo

1. Mở repo gốc trên GitHub.
2. Chọn **Fork**.
3. Đổi repository name theo mẫu trên.
4. Clone fork của bạn:

```bash
git clone <URL_FORK_CUA_BAN>
cd K4_Day14_AI_Evaluation_<Phong>_<MSSV>_<HoTen>
```

### Cách B — Tạo repo mới

Nếu không dùng fork:

1. Tạo repo GitHub mới theo đúng tên quy định.
2. Clone hoặc tải starter code giảng viên cung cấp.
3. Đặt remote của repo cá nhân theo hướng dẫn Git/GitHub của lớp.

Không đưa API key hoặc `.env` lên GitHub.

---

## 2. Cài môi trường

Lab yêu cầu **Python 3.11 trở lên**. Chọn hướng dẫn đúng với hệ điều hành và
kiểm tra version trước khi tạo virtual environment.

### macOS/Linux

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

Nếu `python3 --version` thấp hơn 3.11, cài một bản Python mới hơn rồi gọi đúng
executable, ví dụ `python3.11` hoặc `python3.12`:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

Liệt kê các bản Python đã cài, sau đó chọn một bản từ 3.11 trở lên:

```powershell
py -0p
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

Nếu Python 3.12 là phiên bản đã cài, thay `-3.11` bằng `-3.12`. Với Windows
Command Prompt, activate bằng `.venv\Scripts\activate.bat`.

### Cài dependencies sau khi activate

Các lệnh dưới đây giống nhau trên macOS, Linux và Windows. `python --version`
phải trả về 3.11 trở lên:

```bash
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Kiểm tra import:

```bash
python -c "import openai, dotenv, pytest; print('Environment OK')"
```

---

## 3. Kiểm thử ban đầu và làm Part 1

### 3.1 Chạy baseline tests

Ngay sau khi cài môi trường, chạy toàn bộ test suite một lần:

```bash
pytest tests/ -v
```

Ở starter chưa làm TODO, kết quả dự kiến là **42 tests được collect và 42 tests
fail**. Đây là baseline bình thường, không phải mục tiêu cuối. Quan trọng là
không có lỗi collection, import hoặc thiếu dependency trước khi tests bắt đầu.

Nếu terminal báo `command not found`, `ModuleNotFoundError` hoặc không collect
được tests, xử lý môi trường theo Mục 15 trước khi tiếp tục.

### 3.2 Làm Part 1 trong worksheet

Mở `exercises.md`, hoàn thành **Part 1 — Warm-up** gồm Exercises 1.1–1.3. Part
này chỉ yêu cầu phân tích metrics, bias và CI/CD; chưa sửa `template.py`.

Sau khi điền xong Part 1, quay lại Mục 4 của guide và làm **Part 2 — Core
Coding**. Từ đây nên mở song song hai file:

- `exercises.md` cho danh sách Task và phần cần hoàn thành.
- `guide_lab.md` cho giải thích implementation và checkpoint tests.

---

## 4. Part 2 — Hoàn thiện evaluation core

Đối chiếu **Part 2 — Core Coding** trong `exercises.md` khi làm các Task dưới
đây. Mỗi Task xong phải chạy targeted test tương ứng ở Mục 4.9.

Mở `template.py` và dùng tìm kiếm toàn project của editor với từ khóa `# TODO`.
Nếu muốn tìm bằng terminal:

```bash
# macOS/Linux
grep -n "# TODO" template.py
```

```powershell
# Windows PowerShell
Select-String -Path template.py -Pattern "# TODO"
```

### 4.1 Data models

`QAPair` cần chứa:

- `question`
- `expected_answer`
- `context`
- `metadata`
- `retrieved_contexts`

`EvalResult` cần chứa ba answer scores, optional Context Recall/Precision,
`passed`, `failure_type` và `overall_score()`.

### 4.2 Answer-side metrics

Triển khai Faithfulness, Relevance và Completeness đúng heuristic trong
docstring. Chú ý:

- Dùng `_tokenize()` đã cung cấp.
- Tránh chia cho 0.
- Clamp kết quả vào `[0.0, 1.0]`.
- Không đổi công thức để tối ưu riêng cho dataset của bạn.

### 4.3 Retrieval-side metrics

Context Recall đo coverage trên **union của retrieved chunks**.

Context Precision dùng rank-aware Average Precision. Chunk relevant đứng sớm
phải được điểm cao hơn cùng chunk đứng muộn.

### 4.4 Nối retrieval metrics vào full pipeline

`run_full_eval()` đã có interface:

```python
def run_full_eval(
    self,
    answer: str,
    question: str,
    context: str,
    expected: str,
    contexts: list[str] | None = None,
) -> EvalResult:
```

Yêu cầu:

- `contexts is None`: hai retrieval fields là `None`.
- Có `contexts`: gọi hai retrieval metric functions và lưu scores.
- Pass/failure rule vẫn dựa trên ba answer-side scores như core gốc.
- `BenchmarkRunner.run()` truyền `pair.retrieved_contexts` vào `contexts`.
- `generate_report()` tính average trên các retrieval scores không phải `None`.

### 4.5 LLMJudge

Hoàn thiện `__init__`, `score_response()` và `detect_bias()`. Không cần gọi API
trong unit tests: `LLMJudge` nhận một callable để test dùng mock response.

### 4.6 BenchmarkRunner và regression

Hoàn thiện `run()`, `generate_report()`, `run_regression()` và
`identify_failures()`. Đây là bước nối `agent_fn` với toàn bộ evaluator.

### 4.7 FailureAnalyzer

Hoàn thiện `categorize_failures()`, `find_root_cause()`,
`generate_improvement_suggestions()` và `generate_improvement_log()`.

### 4.8 `python template.py` khác gì `pytest tests/ -v`?

Hai lệnh không thay thế nhau:

| Lệnh | Mục đích | Nó thực sự chạy gì? |
|---|---|---|
| `python template.py` | Manual demo để nhìn output | Chạy `mock_agent` trên 5 sample QA rồi in report/failure analysis. Không gọi API, không chạy real RAG và không kiểm tra mọi function — đặc biệt không cover đầy đủ LLMJudge/regression. Demo chỉ chạy hết sau khi Tasks 1, 2, 4 và 5 đã được implement. |
| `pytest tests/ -v` | Kiểm tra bài làm | Chạy 42 unit tests cho metrics, wiring, judge, runner, regression và failure analyzer. Đây mới là kết quả dùng để xác nhận core đúng. |

`python template.py` chạy thành công **không có nghĩa** 42 tests đã pass. Ngược
lại, khi mới làm Task 1–3, demo có thể vẫn dừng ở TODO của Runner/Analyzer dù
phần vừa làm đã đúng; lúc đó dùng targeted tests dưới đây.

### 4.9 Checkpoint sau từng nhóm TODO

Làm theo đúng thứ tự và chạy test ngay sau mỗi nhóm:

| Checkpoint | Lệnh targeted | Kết quả targeted mong đợi |
|---|---|---:|
| Task 1 — Data models + `overall_score` | `pytest tests/test_solution.py::TestEvalResultOverallScore -v` | 3 passed |
| Task 2 — 5 metrics + `run_full_eval` | `pytest tests/test_solution.py::TestRAGASEvaluator tests/test_solution.py::TestContextMetrics tests/test_solution.py::TestRetrievalMetricWiring::test_run_full_eval_connects_optional_retrieval_metrics -v` | 14 passed, 1 skipped |
| Task 3 — LLMJudge | `pytest tests/test_solution.py::TestLLMJudge -v` | 4 passed |
| Task 4 — Runner + report + regression | `pytest tests/test_solution.py::TestBenchmarkRunner tests/test_solution.py::TestRunRegression tests/test_solution.py::TestRetrievalMetricWiring::test_runner_forwards_retrieved_contexts tests/test_solution.py::TestRetrievalMetricWiring::test_report_includes_retrieval_averages -v` | 11 passed |
| Task 5 — FailureAnalyzer | `pytest tests/test_solution.py::TestFailureAnalyzer tests/test_solution.py::TestGenerateImprovementLog -v` | 9 passed |

Nếu cũng chạy toàn bộ suite sau mỗi checkpoint, số cộng dồn trên starter chuẩn là:

| Trạng thái | Full-suite result |
|---|---:|
| Chưa làm TODO | 0 passed, 42 failed |
| Xong Task 1 | 3 passed, 39 failed |
| Xong Task 2 | 17 passed, 24 failed, 1 skipped |
| Xong Task 3 | 21 passed, 20 failed, 1 skipped |
| Xong Task 4 | 32 passed, 9 failed, 1 skipped |
| Xong Task 5 — hoàn thành phần bắt buộc | 41 passed, 1 skipped |
| Làm thêm `rerank_by_overlap()` bonus | 42 passed |

Test bonus reranking được skip nếu Exercise 3.5 chưa làm. Nếu bạn làm bonus sớm,
con số `skipped` trong bảng sẽ chuyển thành `passed`. Tên test fail quan trọng
hơn việc cố ép đúng con số. Không sửa tests để làm bài pass.

**Test ownership theo function**

| Function/nhóm function | Số public tests trực tiếp |
|---|---:|
| `overall_score()` | 3 |
| Faithfulness / Relevance / Completeness | 3 / 2 / 2 |
| Context Recall / Context Precision | 3 / 3 |
| Retrieval connection trong `run_full_eval()` | 1 |
| `rerank_by_overlap()` | 1 bonus |
| `score_response()` / `detect_bias()` | 3 / 1 |
| `BenchmarkRunner.run()` / `generate_report()` | 3 / 3 |
| `identify_failures()` / `run_regression()` | 2 / 3 |
| Failure categories + suggestions | 2 + 3 |
| Improvement log | 4 |

Data-model fields và `find_root_cause()` còn được kiểm tra gián tiếp qua các
nhóm trên, nên đừng bỏ qua chỉ vì không có một test class riêng.

Khi năm Task bắt buộc đã hoàn thành, full suite phải đạt **41 passed, 1
skipped**. Đánh dấu Part 2 đã xong trong worksheet rồi tiếp tục Mục 5.

---

## 5. Part 3 — Tạo Golden Dataset (Exercise 3.1)

### 5.1 Đọc corpus trước khi viết QA

Corpus nằm trong:

```text
data/technology_store/
```

Đọc `manifest.json` trước để biết 10 documents và use cases, sau đó đọc từng
file Markdown. Corpus synthetic này là source of truth duy nhất của lab, kể cả
khi chính sách khác với kiến thức thực tế.

| Document | Nội dung chính |
|---|---|
| `00_system_scope.md` | Scope, safety, privacy, out-of-scope |
| `01_product_catalog.md` | Products, specifications, compatibility |
| `02_orders_and_payments.md` | Orders, payments, cancellations, installments |
| `03_promotions_and_membership.md` | Promotions, membership, bundles |
| `04_shipping_and_delivery.md` | Shipping, delays, missing packages |
| `05_returns_and_exchanges.md` | Returns, exchanges, refunds, restocking |
| `06_warranty_policy.md` | Warranty coverage, exclusions, proof of purchase |
| `07_repair_and_technical_support.md` | Troubleshooting, repair, service time, data backup |
| `08_accounts_privacy_and_security.md` | Accounts, privacy, security, fraud |
| `09_escalation_and_policy_updates.md` | Escalation, complaints, policy versions |

Không sửa corpus để làm cho expected answer khớp với suy đoán cá nhân. Nếu
expected answer không được corpus hỗ trợ, sửa golden dataset.

### 5.2 File cần điền

`golden_dataset.json` ở root đã có sẵn 20 slots:

- E01–E05: Easy
- M01–M07: Medium
- H01–H05: Hard
- A01–A03: Adversarial

Mỗi record có schema:

```json
{
  "id": "E01",
  "difficulty": "easy",
  "question": "",
  "expected_answer": "",
  "contexts": [
    {
      "source_doc": "",
      "text": ""
    }
  ],
  "attack_type": null
}
```

Chỉ điền hoặc điều chỉnh:

- `question`
- `expected_answer`
- `contexts`

Không đổi `id`, `difficulty` và `attack_type`. Có thể thêm hoặc bớt context
objects theo evidence thực tế; file hoàn thành không được còn context rỗng.

### 5.3 Ý nghĩa từng field

| Field | Cách điền |
|---|---|
| `id` | Đã khóa theo vị trí, không sửa |
| `difficulty` | Đã khóa, không sửa |
| `question` | Câu hỏi do bạn thiết kế |
| `expected_answer` | Expert-written reference answer |
| `contexts` | Evidence hỗ trợ toàn bộ expected answer |
| `source_doc` | Tên chính xác của Markdown source |
| `text` | Đoạn trích nguyên văn từ source |
| `attack_type` | `null` với E/M/H; đã khóa với A01–A03 |

`text` phải là substring nguyên văn của source document. Không paste cả
document; lấy đoạn ngắn đủ bảo vệ expected answer.

### 5.4 Yêu cầu toàn dataset

1. Đúng 20 records và đúng thứ tự IDs.
2. Dùng đủ 10 source documents ít nhất một lần.
3. Mọi evidence xuất hiện nguyên văn trong source tương ứng.
4. Mọi claim trong expected answer được evidence hỗ trợ.
5. Không có hai questions cùng ý.
6. Không dùng kiến thức ngoài corpus.
7. Question và answer nên viết bằng tiếng Anh để khớp corpus và RAG prompt.
8. Expected answer ngắn gọn nhưng giữ đủ dates, amounts, conditions và exceptions.

### 5.5 Easy — factual lookup

Easy thường trả lời trực tiếp từ một đoạn trong một document.

Ví dụ sau dùng **toy hotel domain**, không phải đáp án cho corpus của bài:

```json
{
  "id": "E01",
  "difficulty": "easy",
  "question": "What time does standard check-in begin?",
  "expected_answer": "Standard check-in begins at 3:00 p.m.",
  "contexts": [
    {
      "source_doc": "01_guest_arrival.md",
      "text": "Standard check-in begins at 3:00 p.m. on the arrival date."
    }
  ],
  "attack_type": null
}
```

### 5.6 Medium — multi-step hoặc multi-document

Medium cần kết hợp process/rule hoặc evidence từ 2–3 documents.

Toy example:

```json
{
  "id": "M01",
  "difficulty": "medium",
  "question": "How must a prepaid booking be cancelled, and which charge is not refunded?",
  "expected_answer": "The guest must cancel through the booking portal before the deadline. The eligible room payment is refunded, but the USD 20 processing charge is not refunded.",
  "contexts": [
    {
      "source_doc": "02_cancellation_process.md",
      "text": "A cancellation must be submitted through the booking portal before the applicable deadline."
    },
    {
      "source_doc": "03_payment_and_refunds.md",
      "text": "An eligible prepaid room payment is refundable, but the USD 20 processing charge is non-refundable."
    }
  ],
  "attack_type": null
}
```

### 5.7 Hard — conditions, exceptions hoặc policy versions

Hard không chỉ là question dài. Nó phải yêu cầu xử lý nhiều điều kiện,
effective date, exception hoặc ambiguity có thật trong corpus.

Toy example:

```json
{
  "id": "H01",
  "difficulty": "hard",
  "question": "A guest booked on August 25 for an October stay. Which cancellation-policy version applies?",
  "expected_answer": "Version 1.0 applies because the booking was placed before September 1. The later stay date does not change the version.",
  "contexts": [
    {
      "source_doc": "04_cancellation_policy.md",
      "text": "Version 1.0 applies to bookings placed before September 1. Version 2.0 applies to bookings placed on or after that date."
    },
    {
      "source_doc": "05_policy_updates.md",
      "text": "The booking-placement date determines the applicable policy version; the arrival date does not change it."
    }
  ],
  "attack_type": null
}
```

### 5.8 Adversarial

Ba slots đã khóa:

| ID | Attack type | Mục tiêu |
|---|---|---|
| A01 | `out_of_scope` | Assistant phải từ chối/giới hạn đúng scope |
| A02 | `prompt_injection` | Không làm theo instruction phá system rules |
| A03 | `false_premise_or_ambiguous_trap` | Không xác nhận premise sai hoặc đoán bừa |

Các record này đã gợi ý `00_system_scope.md`. Bạn phải copy evidence phù hợp
vào `text` và viết expected answer đúng với policy. Một adversarial case tốt
kiểm tra behavior cụ thể; nó không chỉ chứa một câu vô nghĩa.

### 5.9 Tự review chất lượng

Với từng record, hỏi:

- Có thể trả lời expected answer chỉ bằng contexts đã chọn không?
- Có claim nào không có evidence không?
- Difficulty có đúng bản chất reasoning không?
- Question có vô tình lộ nguyên câu answer không?
- Có trùng với case khác không?
- Evidence có quá dài hoặc chứa nhiều noise không?

---

## 6. Validate Golden Dataset

Chạy:

```bash
python validate_golden_dataset.py
```

Validator kiểm tra:

- JSON schema và exact fields.
- Đúng IDs/difficulties/attack types.
- Đủ 20 records.
- Question/answer/context không rỗng.
- Không có exact duplicate questions.
- Source document tồn tại trong manifest.
- Evidence là substring nguyên văn.
- Dataset dùng đủ 10 documents.
- Ba adversarial records dùng scope evidence.

Kết quả đạt yêu cầu:

```text
PASS: dataset structure and evidence provenance are valid.
```

Validator không thể tự đánh giá semantic quality hoặc difficulty thật. Bạn vẫn
phải review bằng rubric.

### Khi validator chưa PASS

`text is not a verbatim substring`:

- Copy lại nguyên văn từ Markdown.
- Không tự sửa punctuation, spacing hoặc wording trong evidence.

`Dataset must use every source document`:

- Xem danh sách file còn thiếu.
- Thiết kế case phù hợp; không thêm evidence không liên quan chỉ để đủ coverage.

`expected attack_type` hoặc `expected difficulty`:

- Khôi phục field theo template; chỉ sửa nội dung cần điền.

Khi validator báo `PASS`, quay lại **Exercise 3.1** trong `exercises.md` để ghi
kết quả distribution, coverage và các case đại diện. Sau đó tiếp tục Mục 7 để
sinh actual answers và làm Exercise 3.2.

---

## 7. Cấu hình OpenRouter hoặc OpenAI API

Chỉ `domain_assistant.py` cần API key. OpenRouter được ưu tiên khi cả hai loại
key cùng tồn tại.

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Mở `.env` và chọn một trong hai cấu hình sau.

OpenRouter:

```dotenv
OPENROUTER_API_KEY=<OPENROUTER_KEY_CUA_BAN>
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Hoặc OpenAI trực tiếp:

```dotenv
OPENAI_API_KEY=<API_KEY_CUA_BAN>
OPENAI_MODEL=gpt-4o-mini
```

`.env` đã nằm trong `.gitignore`. Không paste key vào source code, notebook,
artifact, terminal screenshot hoặc commit.

---

## 8. Sinh 20 Actual Answers

Sau khi validator báo PASS:

```bash
python domain_assistant.py
```

Lệnh mặc định tương đương:

```text
python domain_assistant.py --corpus-dir data/technology_store --dataset golden_dataset.json --output artifacts/actual_answers.json --top-k 5
```

Terminal hiển thị từng bước:

```text
[#####---------------] 05/20 | E05 OK (2.1s, 5 chunks)
```

Sau khi hoàn tất, mở `artifacts/actual_answers.json`. Với mỗi ID, kiểm tra:

- Question đúng với golden dataset.
- `actual_answer` có nội dung.
- `retrieved_contexts` có source, chunk ID, text và retrieval score.
- Contexts có liên quan hay chứa noise.
- `error` là `null`.

Nếu run bị lỗi giữa chừng, script dừng và không ghi một artifact hoàn chỉnh giả.
Sửa lỗi rồi chạy lại.

Trong phần bắt buộc, `domain_assistant.py` và corpus là system under evaluation
được cung cấp. Không sửa corpus, đọc expected answer trong lúc generation, hoặc
làm gold leakage để tăng score. Nếu thử cải tiến hệ thống, phải giữ baseline và
mô tả thay đổi rõ ràng như một experiment riêng.

---

## 9. Chạy Evaluation — Exercise 3.2

Điều kiện trước khi chạy:

- Golden dataset đã PASS validator.
- `template.py` đã hoàn thành TODO bắt buộc.
- `artifacts/actual_answers.json` có đủ 20 answers.

Chạy:

```bash
python evaluate_answers.py
```

Lệnh mặc định tương đương:

```text
python evaluate_answers.py --golden golden_dataset.json --actual artifacts/actual_answers.json --output artifacts/benchmark_results.json
```

Adapter thực hiện:

1. Join golden records và actual records bằng ID.
2. Tạo `QAPair` với gold contexts và retrieved contexts.
3. Dùng recorded `agent_fn` trả answer đã sinh.
4. Gọi `BenchmarkRunner.run()` trong `template.py`.
5. Gọi `generate_report()` và `FailureAnalyzer` trong `template.py`.
6. In bảng Exercise 3.2.
7. Lưu `artifacts/benchmark_results.json`.

Nếu thấy:

```text
ERROR: Complete the required TODOs in template.py first
```

thì evaluation core chưa hoàn thành; quay lại Bước 4. Không viết metric mới vào
`evaluate_answers.py` để bypass TODO.

---

## 10. Điền Exercises 3.2 và 3.3

### Exercise 3.2

Copy bảng terminal hoặc đọc `benchmark_results.json` để điền:

- Context Recall
- Context Precision
- Faithfulness
- Relevance
- Completeness
- Overall
- Passed
- Failure Type

Ghi aggregate report và ba cases có Overall Score thấp nhất.

Đừng kết luận chỉ từ pass rate. Ví dụ:

- Recall thấp + Completeness thấp: retriever có thể bỏ sót evidence.
- Recall cao + Precision thấp: lấy đủ evidence nhưng ranking/noise kém.
- Retrieval tốt + Faithfulness thấp: generation có thể thêm claim ngoài context.
- Faithfulness cao + Relevance thấp: answer grounded nhưng không trả đúng intent.

### Exercise 3.3

Thiết kế rubric 1–5 domain-specific. Rubric tốt phải nói rõ:

- Điều kiện để đạt từng mức.
- Cách xử lý missing conditions/exceptions.
- Cách phạt claim không có evidence.
- Cách xử lý privacy/safety failures.
- Cách tránh thưởng answer dài chỉ vì dài.

Không dùng rubric mơ hồ kiểu “5 = tốt, 1 = xấu”.

---

## 11. Viết Reflection

Mở `reflection.md` và dùng ba cases thấp nhất.

Với mỗi case:

1. Đọc question, expected answer và actual answer.
2. So sánh gold evidence với retrieved chunks.
3. Xác định symptom.
4. Đi qua 5 Whys đến root cause có thể hành động.
5. So sánh nhận định của bạn với `find_root_cause()`.
6. Đề xuất fix cụ thể và metric dùng để verify.

Sau đó cluster failures. Ưu tiên fix giải quyết nhiều cases thay vì patch riêng
từng answer.

---

## 12. Bonus — Chỉ làm sau phần bắt buộc

### Exercise 3.4 (+10)

So sánh hai evaluation frameworks trên cùng dataset/input. Không cần tạo file
code bắt buộc mới; ghi phương pháp và kết quả trong `exercises.md`.

### Exercise 3.5 (+5)

Implement `rerank_by_overlap()` hoặc reranker khác, chọn ít nhất năm traces và
đo trước/sau. Giữ nguyên tập chunks để chứng minh reranking tác động ranking,
không tác động union coverage.

Không làm bonus vẫn có thể đạt 100 điểm phần chính.

---

## 13. Tạo Solution và kiểm tra cuối

Khi `template.py` đã hoàn thành, copy file bằng lệnh phù hợp:

```bash
# macOS/Linux
cp template.py solution/solution.py
```

```powershell
# Windows PowerShell
Copy-Item template.py solution/solution.py
```

Sau đó chạy kiểm tra cuối trên mọi hệ điều hành:

```bash
pytest tests/ -v
python validate_golden_dataset.py
```

Lưu ý: tests ưu tiên load `solution/solution.py` nếu file này tồn tại. Vì vậy,
nếu sửa `template.py` sau khi copy, phải copy lại trước lần test cuối.

Kiểm tra bốn deliverables:

```text
solution/solution.py
golden_dataset.json
exercises.md
reflection.md
```

Artifacts là output hỗ trợ, không phải deliverable bắt buộc:

```text
artifacts/actual_answers.json
artifacts/benchmark_results.json
```

---

## 14. Commit và push

Kiểm tra trước khi commit:

```bash
git status
git diff --check
git diff
```

Đảm bảo không có `.env` hoặc API key trong diff. Sau đó commit/push theo workflow
Git của lớp.

---

## 15. Lỗi thường gặp và cách xử lý

Trước khi sửa code, kiểm tra terminal đang ở repo root (`pwd` trên macOS/Linux,
`Get-Location` trên PowerShell) và chạy `python --version` để xác nhận virtual
environment đã được activate.

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Không nhận lệnh `python`, `python3` hoặc `py` | Python chưa được cài hoặc launcher chưa nằm trong `PATH` | Cài Python 3.11+ rồi dùng lệnh tương ứng với hệ điều hành ở Mục 2 |
| `ImportError: cannot import name UTC from datetime` | Venv được tạo bằng Python 3.9/3.10 | Xóa/tạo lại venv bằng Python 3.11+; kiểm tra version trước khi cài requirements |
| `ModuleNotFoundError: openai` hoặc `dotenv` | Chưa activate venv hoặc chưa cài requirements | Activate `.venv`, rồi chạy `python -m pip install -r requirements.txt` |
| Validator liệt kê nhiều field rỗng | `golden_dataset.json` vẫn là form starter | Điền đủ 20 records; đây là lỗi mong đợi trước Exercise 3.1 |
| `text is not a verbatim substring` | Evidence đã bị sửa wording/punctuation | Copy lại nguyên văn đoạn ngắn từ đúng `source_doc` |
| `OPENROUTER_API_KEY or OPENAI_API_KEY is missing from .env` | Thiếu `.env`, key còn placeholder, hoặc chạy sai directory | Copy `.env.example` thành `.env`, điền một key thật và chạy từ repo root |
| `Dataset corpus_id ... does not match assistant corpus_id` | Đã sửa nhầm `corpus_id` | Khôi phục `orbittech-customer-support-v1` |
| `question differs between artifacts` | Golden dataset đã đổi sau lần sinh answers | Validate rồi chạy lại `python domain_assistant.py` để tạo artifact mới |
| `Complete the required TODOs in template.py first` | Core còn `NotImplementedError` | Quay lại checkpoint test tương ứng ở Mục 4.9 |
| Sửa `template.py` nhưng tests vẫn cho kết quả cũ | `solution/solution.py` đã tồn tại và được tests ưu tiên | Copy lại theo lệnh macOS/Linux hoặc Windows ở Mục 13, rồi chạy tests |
| Context Recall/Precision là `None` | Retrieval trace chưa được truyền vào full evaluator | Kiểm tra `actual_answers.json` có chunks, adapter tạo `QAPair.retrieved_contexts`, và Runner truyền `contexts` |

Nếu lỗi không nằm trong bảng, đọc **test name hoặc dòng `ERROR:` đầu tiên** trước;
đừng chỉ nhìn dòng tổng kết cuối terminal. Chạy lại đúng một targeted test bằng
`pytest <test-path> -v` để thu hẹp nguyên nhân.
