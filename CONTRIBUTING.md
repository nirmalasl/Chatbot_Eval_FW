# Spacey DeepEval — Contributing Guide

How to extend, customize, and contribute to this evaluation framework.

---

## Table of Contents

1. [Adding Test Cases](#adding-test-cases)
2. [Adding Custom Metrics](#adding-custom-metrics)
3. [Modifying Configuration](#modifying-configuration)
4. [Creating Custom Output Formats](#creating-custom-output-formats)
5. [Code Style & Best Practices](#code-style--best-practices)
6. [Troubleshooting Development](#troubleshooting-development)

---

## Adding Test Cases

### Step 1: Define the Test Case

Open `spacey_deepeval_v4.py` and find the `EVAL_CASES` list (around line 120).

Add your test case before the closing bracket:

```python
EvalCase(
    "E-17",  # Next available ID (increment from E-16)
    "your query text here",
    "Expected behavior description — what the bot should do.",
    history=[
        # Optional: include prior conversation turns for multi-turn tests
        {"role": "user", "content": "first message"},
        {"role": "assistant", "content": "first response"},
    ],
    tags={"tag1", "tag2", ...},  # Choose from existing tags (below)
)
```

### Step 2: Choose Appropriate Tags

Tags determine which metrics are applied. Pick from:

| Tag | Metrics Added | Use When |
|-----|---------------|----------|
| `search` | TaskCompletionMetric | Bot should return space results |
| `clarify` | (core only) | Bot should ask a question, not search yet |
| `multi-turn` | KnowledgeRetentionMetric | Test involves prior conversation context |
| `off-topic` | TopicAdherenceMetric | Bot should redirect off-topic requests |
| `empty` | GEval(Empathy) | Expect no results; test empathetic response |
| `handoff` | TaskCompletionMetric | Bot should offer human agent contact |
| `amenity` | GEval(AmenityAccuracy) | Test involves amenity filters |
| `chip-removal` | GEval(ChipRemoval) | Test filter chip removal |
| `browse-mode` | GEval(ModeLanguage) | Test browse vs availability mode language |

**Example:**

```python
EvalCase(
    "E-17",
    "show me workspaces with free WiFi",
    "Should return workspace cards filtered to show only those with WiFi amenity.",
    tags={"search", "amenity"},  # Triggers 5 metrics total
)
```

### Step 3: Run Your Test

Test locally first:

```bash
# See your new test in dry-run
python spacey_deepeval_v4.py --dry-run | grep E-17

# Run only your test (if you modify the script to allow filtering)
python spacey_deepeval_v4.py --tags search amenity  # Runs all with these tags
```

### Step 4: Validate Results

After running, check:
- ✓ Query was sent correctly
- ✓ Metrics applied as expected
- ✓ Response quality reasonable
- ✓ Score aligned with response quality

**Example test case template:**

```python
EvalCase(
    "E-18",
    "I want a video shoot in Galle",
    "Should return video shoot spaces in Galle, or empathetically suggest Colombo if none available.",
    history=[],
    tags={"search"},
)
```

---

## Adding Custom Metrics

### Option A: Use Existing Metrics with Custom Config

All metrics from deepeval can be configured. Example:

```python
from deepeval.metrics import GEval

# Create a custom-configured GEval metric
custom_metric = GEval(
    name="MyCustomMetric",
    model="gpt-4o-mini",
    criteria="My custom evaluation criteria here.",
    evaluation_params=["query", "expected_output", "actual_output"],
)
```

### Option B: Define a New Tag + Metric

1. **Choose a new tag name** (e.g., `"location-switching"`)

2. **Update tag assignment logic** in the script:

Find this section (around line 120–150):
```python
def get_metrics_for_case(case: EvalCase) -> list:
    metrics = [
        AnswerRelevancyMetric(),
        GEval(name="Correctness", ...),
        GEval(name="Conciseness", ...),
    ]
    
    if "search" in case.tags:
        metrics.append(TaskCompletionMetric())
    
    # ADD YOUR NEW TAG HERE:
    if "location-switching" in case.tags:
        metrics.append(GEval(
            name="LocationSwitch",
            model=EVAL_MODEL,
            criteria="Did the bot correctly switch location filters?",
            evaluation_params=["query", "expected_output", "actual_output"],
        ))
    
    return metrics
```

3. **Use your new tag** in test cases:

```python
EvalCase(
    "E-19",
    "actually in Kandy",
    "Bot should remember it's a photo shoot and switch location to Kandy.",
    history=[{"role": "user", "content": "photo shoot in Colombo"}],
    tags={"search", "multi-turn", "location-switching"},  # Your new tag!
)
```

### Option C: Create a Custom Metric Class

Advanced: Extend deepeval's `Metric` class:

```python
from deepeval.metrics import Metric
from deepeval.test_case import LLMTestCase

class CustomSpaceyMetric(Metric):
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
    
    def measure(self, test_case: LLMTestCase) -> float:
        """
        Implement custom scoring logic.
        test_case has: input, expected_output, actual_output
        """
        # Your scoring logic here
        # Return 0.0–1.0
        score = self._evaluate_with_llm(
            test_case.input,
            test_case.expected_output,
            test_case.actual_output
        )
        return score
    
    @property
    def __name__(self) -> str:
        return "CustomSpaceyMetric"
```

Then use:
```python
if "my-tag" in case.tags:
    metrics.append(CustomSpaceyMetric())
```

---

## Modifying Configuration

### Changing API Endpoint

**Default:**
```python
BASE_URL = "https://api-prod-ecs.millionspaces.com/api/search/agent/chat"
```

**To test against staging:**
```python
BASE_URL = "https://api-staging-ecs.millionspaces.com/api/search/agent/chat"
```

### Changing Evaluation Model

**Default:**
```python
EVAL_MODEL = "gpt-4o-mini"
```

**For higher accuracy (slower, more expensive):**
```python
EVAL_MODEL = "gpt-4-turbo"  # or "gpt-4"
```

**For speed (cheaper, less accurate):**
```python
EVAL_MODEL = "gpt-3.5-turbo"
```

### Changing Pass Threshold

**Default:**
```python
PASS_THRESHOLD = 0.5  # Pass if score ≥ 0.5
```

**Stricter (A/B grades only):**
```python
PASS_THRESHOLD = 0.75
```

**More lenient:**
```python
PASS_THRESHOLD = 0.4
```

### Adding Authentication

If Spacey API returns 403:

```python
AUTH_HEADERS: dict = {
    "Cookie": "sessionid=abc123def456...",
    "Authorization": "Bearer your_token_here",
}
```

Or get from environment:
```python
AUTH_HEADERS: dict = {
    "Authorization": f"Bearer {os.getenv('SPACEY_AUTH_TOKEN', '')}",
}
```

---

## Creating Custom Output Formats

### Step 1: Write a Formatter Function

```python
def save_to_excel(results: dict, filename: str) -> None:
    """Export results to Excel with formatting."""
    import openpyxl
    
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Add headers
    ws.append(["Test ID", "Query", "Result", "Pass Rate"])
    
    # Add data
    for result in results['tests']:
        ws.append([
            result['id'],
            result['query'],
            result['result'],
            result['pass_rate'],
        ])
    
    wb.save(filename)
    print(f"✓ Saved to {filename}")
```

### Step 2: Add Command-Line Flag

In the argument parser section (around line 500):

```python
parser.add_argument(
    '--excel',
    action='store_true',
    help='Save results to Excel format'
)
```

### Step 3: Call in Main Function

```python
if __name__ == "__main__":
    # ... existing code ...
    
    if args.excel:
        save_to_excel(results, "spacey_deepeval_results.xlsx")
```

### Step 4: Test

```bash
python spacey_deepeval_v4.py --excel
```

---

## Code Style & Best Practices

### Python Style Guide (PEP 8)

- **Indentation:** 4 spaces
- **Line length:** Max 88 characters
- **Naming:**
  - `Classes`: PascalCase
  - `functions`: snake_case
  - `constants`: UPPER_SNAKE_CASE

### Docstrings

Use Google-style docstrings:

```python
def query_spacey(messages: list, retry_count: int = 0) -> str:
    """
    Query the Spacey API and return the assistant response.
    
    Args:
        messages: List of message dicts with 'role' and 'content'.
        retry_count: Current retry attempt (incremented on failure).
    
    Returns:
        Assistant reply text.
    
    Raises:
        RequestException: If API fails after MAX_RETRIES attempts.
    """
    # Implementation...
```

### Error Handling

Always handle errors gracefully:

```python
try:
    response = requests.post(url, json=data, timeout=TIMEOUT)
    response.raise_for_status()
except requests.Timeout:
    print(f"❌ Timeout: {url}")
    # Retry or log
except requests.HTTPError as e:
    print(f"❌ HTTP {e.response.status_code}: {e}")
    # Handle appropriately
```

### Type Hints

Always include types:

```python
def calculate_pass_rate(passed: int, total: int) -> float:
    """Calculate pass rate percentage."""
    return (passed / total) * 100 if total > 0 else 0.0
```

---

## Troubleshooting Development

### Test runs slowly (>5 min for 15 tests)

**Cause:** LLM scoring is network-dependent.

**Solution:**
- Run subset: `--tags search` (fewer tests)
- Use faster model: `EVAL_MODEL = "gpt-3.5-turbo"`
- Increase `PAUSE` if rate-limited

### Metric scoring seems off

**Cause:** LLM-based metrics can be subjective.

**Solution:**
- Review metric prompt/criteria
- Adjust `PASS_THRESHOLD` if needed
- Manually inspect failing cases
- File issue with specific example

### New test case always fails

**Cause:** Expected behavior too strict or response format misunderstood.

**Solution:**
1. Run with `--dry-run` to see exact query/expected
2. Manually test bot with that query
3. Review response and metric reasoning
4. Adjust expected description if needed

### Changes not taking effect

**Cause:** Python may cache modules.

**Solution:**
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +

# Run again
python spacey_deepeval_v4.py
```

---

## Submitting Changes

If you want to contribute back:

1. **Fork or branch** the repository
2. **Make changes** following above guidelines
3. **Test thoroughly** with `--dry-run` and sample runs
4. **Document** your changes in relevant .md files
5. **Submit PR** with clear description

---

## Resources

- **DeepEval Documentation:** https://github.com/confident-ai/deepeval
- **Spacey Product Spec:** [SPACEY_V2_BEHAVIOUR.md](SPACEY_V2_BEHAVIOUR.md)
- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Metrics Guide:** [METRICS_REFERENCE.md](METRICS_REFERENCE.md)

---

**Questions?** See README.md or review existing test cases for patterns.
