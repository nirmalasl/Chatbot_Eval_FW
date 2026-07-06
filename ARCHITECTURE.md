# Spacey DeepEval — Architecture & Design

How the framework works under the hood.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Evaluation Suite                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Spacey DeepEval v4 (spacey_deepeval_v4.py)         │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│    ┌────────────────────┼────────────────────┐               │
│    ▼                    ▼                    ▼               │
│  ┌──────────┐      ┌──────────┐      ┌────────────┐         │
│  │   Test   │      │ Spacey   │      │  DeepEval  │         │
│  │  Cases   │──────│   API    │─────▶│  Metrics   │         │
│  │   (15+)  │      │ (Query & │      │   (7)      │         │
│  └──────────┘      │ Response)│      └────────────┘         │
│                    └──────────┘             │                │
│                         ▲                   │                │
│                         │                   ▼                │
│                    ┌─────────┐      ┌──────────────┐         │
│                    │ OpenAI  │◀─────│ LLM Scoring  │         │
│                    │ (LLM)   │      │  via GPT-4   │         │
│                    └─────────┘      └──────────────┘         │
│                                            │                 │
│                                            ▼                 │
│                                      ┌────────────┐          │
│                                      │  Results   │          │
│                                      │ (CSV/HTML/ │          │
│                                      │   JSON)    │          │
│                                      └────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. **Test Cases Module**

**File:** `spacey_deepeval_v4.py` (lines ~120–300)

**What it does:**
- Defines 15+ `EvalCase` objects
- Each case has:
  - `id`: Unique identifier (E-01, E-02, etc.)
  - `query`: User message to test
  - `expected`: What the correct response should be
  - `history`: Prior conversation turns (for multi-turn tests)
  - `tags`: Categorization (search, multi-turn, off-topic, etc.)

**Data structure:**
```python
@dataclass
class EvalCase:
    id: str                              # "E-01"
    query: str                           # "meeting room in Colombo"
    expected: str                        # "Should return results..."
    history: list = field(...)           # Previous turns
    tags: set = field(...)               # {"search", "multi-turn"}
```

**Tags drive metric selection** (see Metric Assignment section below).

---

### 2. **API Integration Module**

**File:** `spacey_deepeval_v4.py` (lines ~300–400)

**What it does:**
- Sends user queries to Spacey chatbot API
- Handles authentication (headers, cookies, tokens)
- Manages retries on network errors
- Implements rate limiting (PAUSE between calls)
- Parses JSON responses

**Key functions:**
- `query_spacey(messages)` → sends request, returns assistant reply
- `build_headers()` → constructs auth headers from config
- `retry_on_error(func, max_retries)` → wraps network calls

**Request format:**
```json
{
  "messages": [
    {"role": "user", "content": "meeting room in Colombo"},
    {"role": "assistant", "content": "Here are some options..."}
  ]
}
```

**Response format:**
```json
{
  "reply": "Here are meeting rooms in Colombo for you.",
  "cards": [...],
  "chips": [{"label": "Meeting Room", "type": "type"}]
}
```

---

### 3. **Metric Assignment Engine**

**File:** `spacey_deepeval_v4.py` (lines ~100–120)

**How metrics are assigned:**

Each test case has **core metrics** + **selective metrics** based on tags:

```
All tests
├─ AnswerRelevancyMetric
├─ GEval(Correctness)
└─ GEval(Conciseness)

Tags → Additional metrics:
├─ "search" → + TaskCompletionMetric
├─ "multi-turn" → + KnowledgeRetentionMetric
├─ "off-topic" → + TopicAdherenceMetric
├─ "empty" → + GEval(Empathy)
├─ "amenity" → + GEval(AmenityAccuracy)
├─ "chip-removal" → + GEval(ChipRemoval)
└─ "browse-mode" → + GEval(ModeLanguage)
```

**Pseudocode:**
```python
def get_metrics_for_case(case: EvalCase):
    metrics = [
        AnswerRelevancyMetric(),
        GEval(name="Correctness", ...),
        GEval(name="Conciseness", ...),
    ]
    
    if "search" in case.tags:
        metrics.append(TaskCompletionMetric())
    if "multi-turn" in case.tags:
        metrics.append(KnowledgeRetentionMetric())
    # ... etc
    
    return metrics
```

---

### 4. **DeepEval Evaluation Engine**

**File:** `spacey_deepeval_v4.py` (uses deepeval library)

**What it does:**
- Sends each response + expected outcome to GPT-4o-mini
- Scores response on each metric (0.0–1.0)
- Returns detailed reasoning (LLM can explain why it scored X)

**Metrics library:**
```python
from deepeval.metrics import (
    AnswerRelevancyMetric,
    TaskCompletionMetric,
    TopicAdherenceMetric,
    KnowledgeRetentionMetric,
    GEval,
)
```

**Scoring flow:**
```
Response text + Expected behavior
          ↓
      GPT-4o-mini
          ↓
   Reasoning + Score (0–1)
          ↓
   Compare to PASS_THRESHOLD (0.5 default)
          ↓
   PASS (if ≥ 0.5) or FAIL (if < 0.5)
```

---

### 5. **Results Aggregation Module**

**File:** `spacey_deepeval_v4.py` (lines ~400–500)

**What it does:**
- Collects all metric scores per test
- Determines pass/fail per test (all metrics must pass)
- Calculates overall pass rate
- Formats output (console, CSV, HTML, JSON)

**Pass logic:**
```python
def is_test_pass(case_results):
    for metric_score in case_results.metric_scores:
        if metric_score < PASS_THRESHOLD:
            return False
    return True
```

**Summary calculation:**
```
pass_rate = (num_passed / total_tests) * 100
```

---

## Execution Flow

### Scenario: Running `python spacey_deepeval_v4.py --html`

```
1. Parse arguments
   └─ --html flag detected
   
2. Load configuration
   └─ Read BASE_URL, TIMEOUT, EVAL_MODEL, PASS_THRESHOLD, etc.
   
3. Load environment
   └─ Read .env for OPENAI_API_KEY
   
4. Load test cases
   └─ Initialize EVAL_CASES list (E-01 through E-16+)
   
5. For each test case:
   
   a. Query Spacey API
      └─ POST to BASE_URL with test case query + history
      └─ Retry on error (up to MAX_RETRIES)
      └─ Wait PAUSE seconds before next query
      
   b. Get assistant response
      └─ Parse JSON response
      
   c. Assign metrics
      └─ Determine which metrics to apply based on tags
      
   d. Evaluate with DeepEval
      └─ For each metric:
         └─ Call metric.measure(actual, expected)
         └─ Get score (0–1)
         └─ Record reasoning
      
   e. Aggregate metric scores
      └─ Check if all ≥ PASS_THRESHOLD
      └─ Mark test PASS or FAIL
   
   f. Print progress (if not --fail-fast)
   └─ Or exit immediately (if --fail-fast and FAIL)
   
6. Aggregate all results
   └─ Count passes, fails, errors
   └─ Calculate pass rate %
   
7. Format output
   └─ Print console summary
   └─ If --output: write CSV
   └─ If --html: generate and open HTML report
   └─ If --json: write JSON
   
8. Exit
   └─ Return 0 (all pass) or 1 (any fail)
```

---

## Configuration Hierarchy

```
Defaults (in script)
       ↓
   Environment (.env)
       ↓
   Command-line flags
       ↓
   Runtime values
```

**Example:**
```python
# Default
PASS_THRESHOLD = 0.5

# Can be overridden at runtime if flag added:
# python spacey_deepeval_v4.py --threshold 0.7
```

---

## Error Handling

### Network Errors

```python
try:
    response = requests.post(url, ...)
except (requests.Timeout, requests.ConnectionError) as e:
    if retry_count < MAX_RETRIES:
        # Wait and retry
        time.sleep(2)
        return query_spacey(messages, retry_count + 1)
    else:
        # Mark as ERROR
        return None
```

### API Errors

| Status | Action |
|--------|--------|
| 403 Forbidden | Check AUTH_HEADERS |
| 401 Unauthorized | Check OpenAI API key |
| 429 Too Many Requests | Increase PAUSE, retry later |
| 500+ Server Error | Retry (up to MAX_RETRIES) |

### LLM Scoring Errors

If DeepEval metric fails:
- Log error with test case ID
- Mark as ERROR (not FAIL)
- Continue to next test
- Report errors in summary

---

## Tag System Design

**Why tags?**
- Different test types need different metrics
- Easy to filter/run subsets (e.g., `--tags search multi-turn`)
- Extensible: add new tag + new metric, no refactor needed

**Tag workflow:**
```
User defines tag on EvalCase
         ↓
       is_tag_in_case = case.has_tag("search")
         ↓
    Metric assignment checks is_tag_in_case
         ↓
    If True, add metric to evaluation
         ↓
    Evaluate with that metric
```

**Adding a new tag:**
1. Define tag name (e.g., "new-feature")
2. Add to EVAL_CASE tags: `tags={"new-feature"}`
3. Add metric assignment in `get_metrics_for_case()`:
   ```python
   if "new-feature" in case.tags:
       metrics.append(GEval(name="NewFeature", ...))
   ```

---

## Output Format Design

### Console (stdout)

- Real-time progress per test
- Color-coded pass (green) / fail (red)
- Summary at end

### CSV

- One row per test
- Columns: ID, tags, query, expected, metric scores, result
- Easy to import into Excel/Sheets for analysis

### HTML

- Interactive dashboard
- Charts (pass/fail distribution, metric heatmap)
- Drill-down per test
- Shareable, no dependencies needed

### JSON

- Machine-readable
- Nests results for programmatic access
- Suitable for CI/CD pipelines

---

## Performance Considerations

### Bottlenecks

| Component | Time | Notes |
|-----------|------|-------|
| Spacey API query | 2–5 sec | Network + backend search |
| DeepEval scoring | 3–8 sec per metric | LLM invocation (OpenAI API) |
| Total per test | ~15–30 sec | 3–5 metrics × 3–8 sec |
| Full suite (15 tests) | ~3–8 min | Depends on network, parallelizable |

### Optimization Strategies

1. **Run subset of tests:** `--tags search` (faster feedback)
2. **Increase PAUSE if rate-limited:** Better for production
3. **Use faster LLM:** `EVAL_MODEL = "gpt-3.5-turbo"` (less accurate)
4. **Batch tests:** Run multiple in parallel (future enhancement)

---

## Extensibility

### Adding a New Test Case

1. Append to `EVAL_CASES` list:
```python
EvalCase(
    "E-17", "your query here",
    "Expected behavior...",
    history=[...],  # optional
    tags={"tag1", "tag2"},  # choose from existing or new
)
```

2. If new tag, add metric assignment in `get_metrics_for_case()`.

### Adding a New Metric

1. Import from deepeval or define custom:
```python
from deepeval.metrics import MyCustomMetric
```

2. Update `get_metrics_for_case()`:
```python
if "my-tag" in case.tags:
    metrics.append(MyCustomMetric(...))
```

### Adding a New Output Format

1. Implement formatter function:
```python
def save_to_custom_format(results, filename):
    with open(filename, 'w') as f:
        f.write(format_results(results))
```

2. Add command-line flag and condition:
```python
if args.custom_format:
    save_to_custom_format(results, "output.custom")
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `deepeval` | Latest | Metric definitions & scoring |
| `requests` | 2.28+ | HTTP calls to Spacey API |
| `python-dotenv` | 0.19+ | .env file parsing |
| `openai` | (via deepeval) | LLM integration |

---

## Future Enhancements

- [ ] Parallel test execution (speed up 15+ tests)
- [ ] Custom metric definitions (user-defined scoring)
- [ ] Database storage (persistent result history)
- [ ] Webhook integration (POST results to CI/CD)
- [ ] Regression detection (auto-flag declining metrics)
- [ ] Comparative analysis (before/after scores)

---

**See Also:**
- [README.md](README.md) — Usage guide
- [SPACEY_V2_BEHAVIOUR.md](SPACEY_V2_BEHAVIOUR.md) — Product specification
- [TEST_CASES.md](TEST_CASES.md) — Detailed test case reference
