# DeepEval — Chatbot Evaluation Framework

A comprehensive evaluation framework for testing **Spacey**, the AI-powered workspace search and booking chatbot on MillionSpaces (Sri Lanka). This framework uses **DeepEval** metrics to systematically evaluate chatbot response quality across multiple dimensions.

---

## 📋 Table of Contents

- [Overview](#overview)
- [What is Spacey?](#what-is-spacey)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Evaluation Metrics](#evaluation-metrics)
- [Test Cases & Tags](#test-cases--tags)
- [Output Formats](#output-formats)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

**Spacey DeepEval** is an automated evaluation suite that tests a chatbot agent's ability to:

- **Understand** free-text queries about workspace search and booking
- **Search** live MillionSpaces inventory based on filters (type, location, budget, date, capacity)
- **Return results** as space cards with appropriate metadata
- **Handle** progressive search refinement and multi-turn conversations
- **Recover gracefully** from edge cases, empty results, and off-topic queries

The framework includes **42 predefined test cases** covering core functionality, filter handling, multi-turn context retention, amenity filtering, chip removal, and error scenarios.

---

## What is Spacey?

**Spacey** is a conversational AI assistant that helps users find and book workspaces. Key features:

| Feature | Details |
|---------|---------|
| **Not a form** | Free-text chat, not step-by-step questionnaire |
| **Progressive search** | Minimum input = space type; location/date/budget optional |
| **Live inventory** | Queries against real MillionSpaces availability |
| **Space cards** | Results shown as interactive cards, not text lists |
| **Filter chips** | Removable filters (type, location, date, budget, capacity) |
| **Two modes** | **Browse** (no date) vs **Availability** (with date) |
| **Multi-turn** | Remembers conversation context across turns |

**Supported space types:** Individual Workspace, Private Office, Virtual Office, Meeting Space, Interview Room, Team Building, Training, Photo Shoot, Video Shoot.

---

## Prerequisites

### System Requirements
- **Python 3.8+**
- **Internet connection** (to reach Spacey API and OpenAI)

### API Access
- **Spacey endpoint:** `https://api-prod-ecs.millionspaces.com/api/search/agent/chat`
- **OpenAI API key:** Required for LLM-based evaluation metrics (GPT-4o-mini)

### Software Dependencies

Install with pip:

```bash
pip install deepeval requests python-dotenv
```

---

## Installation

### 1. Clone or download this repository

```bash
cd "d:\Chatbot 6"
```

### 2. Install Python dependencies

```bash
pip install deepeval requests python-dotenv
```

### 3. Create a `.env` file in the project root

```env
OPENAI_API_KEY=sk-your-key-here
```

**Where to get your OpenAI API key:**
1. Visit https://platform.openai.com/api-keys
2. Create or copy an existing API key
3. Paste into `.env`

### 4. (Optional) Add authentication headers

If the Spacey endpoint returns **403 Forbidden**, add session credentials to the script:

Open `spacey_deepeval_v4.py` and update:

```python
AUTH_HEADERS: dict = {
    "Cookie":        "your_session_cookie_here",
    "Authorization": "Bearer your_token_here",
}
```

---

## Configuration

### Key Settings in `spacey_deepeval_v4.py`

| Setting | Default | Purpose |
|---------|---------|---------|
| `BASE_URL` | `https://api-prod-ecs.millionspaces.com/...` | Spacey API endpoint |
| `TIMEOUT` | 30 sec | Max wait time per API call |
| `PAUSE` | 1.5 sec | Delay between requests (rate limiting) |
| `MAX_RETRIES` | 2 | Retries on network errors |
| `FUTURE_DATE` | Today + 20 days | Default date for availability tests |
| `EVAL_MODEL` | `gpt-4o-mini` | LLM for evaluation metrics |
| `PASS_THRESHOLD` | 0.5 | Min score (0–1) to pass a metric |

### Adjusting Configuration

Edit the `CONFIG` section at the top of the script:

```python
# Change timeout for slow networks
TIMEOUT = 45

# Use a different LLM
EVAL_MODEL = "gpt-4-turbo"

# Stricter pass threshold
PASS_THRESHOLD = 0.7
```

---

## Usage

### Basic Run

Run the full evaluation suite:

```bash
python spacey_deepeval_v4.py
```

This will:
1. Load all 15+ test cases
2. Query the Spacey API for each
3. Evaluate responses using DeepEval metrics
4. Print results to the console
5. Exit with summary stats

### Command-Line Options

| Option | Purpose |
|--------|---------|
| `--dry-run` | Print test cases and config without making API calls |
| `--output` | Save results to `spacey_deepeval_results.csv` |
| `--html` | Generate HTML report (`spacey_deepeval_report.html`) |
| `--json` | Save results to JSON format |
| `--fail-fast` | Stop on first metric failure |
| `--tags TAG1 TAG2 ...` | Run only specific tags (see [Test Cases & Tags](#test-cases--tags)) |

### Examples

#### Preview test cases without API calls

```bash
python spacey_deepeval_v4.py --dry-run
```

#### Run full evaluation and save CSV results

```bash
python spacey_deepeval_v4.py --output
```

#### Generate HTML report (best for sharing)

```bash
python spacey_deepeval_v4.py --html
```

#### Run only "search" and "multi-turn" tests

```bash
python spacey_deepeval_v4.py --tags search multi-turn
```

#### Combine: run specific tags and stop on first failure

```bash
python spacey_deepeval_v4.py --tags search amenity --fail-fast
```

#### Run with all output formats

```bash
python spacey_deepeval_v4.py --output --html --json
```

---

## Evaluation Metrics

Each test case is evaluated on **1 to 7 metrics** depending on test type:

### Core Metrics (Every Test Case)

| Metric | What It Checks |
|--------|----------------|
| **AnswerRelevancyMetric** | Does the reply address the user's query? |
| **GEval (Correctness)** | Does the reply match expected behavior? |
| **GEval (Conciseness)** | Is the reply appropriately short (1–2 sentences)? |

### Selective Metrics (Tag-Driven)

| Tag | Metric Added | What It Checks |
|-----|--------------|----------------|
| `search` | **TaskCompletionMetric** | Did the bot return search results? |
| `off-topic` | **TopicAdherenceMetric** | Did the bot stay on workspace booking? |
| `multi-turn` | **KnowledgeRetentionMetric** | Did the bot remember prior context? |
| `empty` | **GEval (Empathy)** | Empathetic tone on zero-result cases? |
| `amenity` | **GEval (AmenityAccuracy)** | Were correct amenity filters applied? |
| `chip-removal` | **GEval (ChipRemoval)** | Did the bot drop the right filter cleanly? |
| `browse-mode` | **GEval (ModeLanguage)** | Correct "browse" vs "availability" language? |

### Scoring

- **Scale:** 0 to 1 (continuous)
- **Pass threshold:** 0.5 (default; configurable)
- **0.75–1.0:** Strong pass
- **0.5–0.74:** Marginal pass
- **<0.5:** Fail

---

## Test Cases & Tags

The framework includes **42 predefined test cases** organized into 5 groups:

### Core Search (E-01 to E-04)
- **E-01:** Meeting room in Colombo → should return results
- **E-02:** "I need a space" → should ask what type
- **E-03:** "What types do you have?" → should list 9 types
- **E-04:** "Colombo" (location only) → should ask for space type

### Filters & Refinement (E-05 to E-07)
- **E-05:** Budget filter ("under 5000") → should apply cap
- **E-06:** Multi-filter with date ("20 people on [date]") → availability mode
- **E-07:** Pricing hedge ("how much does coworking cost?") → should not give fixed price

### Multi-Turn Context (E-08 to E-09)
- **E-08:** "actually private office" (after meeting room search) → switch context
- **E-09:** "under 8000" (after city + type set) → apply filter in context

### Handoff & Edge Cases (E-10 to E-15)
- **E-10:** "speak to a real person" → offer human handoff
- **E-11:** "weather in Colombo" (off-topic) → redirect politely
- **E-12:** "Hi" → warm greeting
- **E-13:** "video shoot in Jaffna under 500" (no results) → empathetic + alternatives
- **E-14:** "dedicated desk" (unsupported type) → list alternatives
- **E-15:** "private office" → return results (don't demand city)

### Progressive Search & Modes (E-16–E-27)
- **E-16:** "photo studio" (type-only) → all Sri Lanka, no location demand
- **E-17–E-18:** Availability mode language; country-wide queries
- **E-19–E-21:** Unsupported types and name aliases (boardroom, hot desk)
- **E-22–E-23:** Multi-filter parsing; mid-chat type changes
- **E-24–E-27:** Empty results with empathy; alternate handoff phrasing; off-topic jokes

### Amenity Filters (E-28–E-35)
- **E-28–E-29:** Single amenity filters (WiFi, Video Conferencing)
- **E-30–E-31:** Multi-amenity searches (2–3 amenities combined)
- **E-32–E-33:** Natural language amenity mapping; location + amenity combos
- **E-34–E-35:** Multi-turn amenity refinement; impossible combinations (empty result empathy)

### Chip Removal & Filter Management (E-36–E-38)
- **E-36–E-37:** Remove budget/location chips; retain other filters
- **E-38:** Remove date chip; revert to browse mode

### Missing Space Types (E-39–E-42)
- **E-39:** Interview Room
- **E-40:** Team Building
- **E-41:** Virtual Office
- **E-42:** Video studio (alias for Video Shoot)

### Tag Reference

| Tag | Meaning |
|-----|---------|
| `search` | Bot should return space results |
| `clarify` | Bot should ask a question, not results |
| `off-topic` | Bot should redirect to workspace booking |
| `multi-turn` | Conversation has prior history; context must carry |
| `handoff` | Bot should trigger human-agent contact form |
| `empty` | Expect no results; empathetic response + alternatives |
| `amenity` | Query involves amenity filters |
| `chip-removal` | Synthetic message from chip click; filter removal |
| `browse-mode` | Response must use browse-mode language (no "Available" without date) |

---

## Output Formats

### Console Output (Default)

```
═══════════════════════════════════════════════════════════════════════════════
Spacey DeepEval — Results
═══════════════════════════════════════════════════════════════════════════════

Test E-01: meeting room in Colombo
  Tags: search
  Metrics:
    ✓ AnswerRelevancyMetric:      0.92
    ✓ GEval (Correctness):        0.88
    ✓ GEval (Conciseness):        0.95
    ✓ TaskCompletionMetric:       0.87
  Result: PASS

Test E-02: I need a space
  Tags: clarify
  Metrics:
    ✓ AnswerRelevancyMetric:      0.85
    ✓ GEval (Correctness):        0.79
    ✗ GEval (Conciseness):        0.42 (FAIL)
  Result: FAIL

───────────────────────────────────────────────────────────────────────────────
Summary: 13 pass, 2 fail, 0 error | Pass rate: 86.7%
```

### CSV Output (`--output`)

```csv
test_id,tags,query,expected,answer_relevancy,correctness,conciseness,task_completion,topic_adherence,knowledge_retention,empathy,result
E-01,"search","meeting room in Colombo","Should mention meeting rooms available in Colombo...",0.92,0.88,0.95,0.87,,,,PASS
E-02,"clarify","I need a space","Should ask a clarifying question...",0.85,0.79,0.42,,,,,FAIL
...
```

### HTML Report (`--html`)

Opens in browser or can be shared. Includes:
- Summary dashboard (pass rate, charts)
- Per-test breakdown with metrics
- Failure details and recommendations

### JSON Output (`--json`)

Structured format for integration with CI/CD:

```json
{
  "summary": {
    "total": 15,
    "passed": 13,
    "failed": 2,
    "errors": 0,
    "pass_rate": 0.867
  },
  "tests": [
    {
      "id": "E-01",
      "tags": ["search"],
      "query": "meeting room in Colombo",
      "metrics": {
        "answer_relevancy": 0.92,
        "correctness": 0.88,
        "conciseness": 0.95,
        "task_completion": 0.87
      },
      "result": "PASS"
    }
  ]
}
```

---

## Examples

### Example 1: Quick Validation (Dry Run)

```bash
python spacey_deepeval_v4.py --dry-run
```

**Output:** Lists all 15 test cases without calling the API. Use to verify configuration.

### Example 2: Full Evaluation with HTML Report

```bash
python spacey_deepeval_v4.py --html
```

**Output:** Generates `spacey_deepeval_report.html`. Open in browser to see visual pass/fail breakdown.

### Example 3: Test Specific Features

```bash
python spacey_deepeval_v4.py --tags search multi-turn amenity --output
```

**Output:** Runs only tests tagged as `search`, `multi-turn`, or `amenity`, and saves results to CSV.

### Example 4: Regression Testing (Fail Fast)

```bash
python spacey_deepeval_v4.py --fail-fast
```

**Output:** Stops evaluation immediately on first failing metric. Useful for quick feedback during development.

### Example 5: Generate All Reports

```bash
python spacey_deepeval_v4.py --output --html --json
```

**Output:** Creates `spacey_deepeval_results.csv`, `spacey_deepeval_report.html`, and JSON results all at once.

---

## Troubleshooting

### Issue: "403 Forbidden" from Spacey API

**Cause:** Missing or expired authentication.

**Solution:**
1. Check that `.env` contains a valid `OPENAI_API_KEY`
2. If you have session credentials, add them to `AUTH_HEADERS` in the script:
   ```python
   AUTH_HEADERS: dict = {
       "Cookie":        "sessionid=your_value_here",
       "Authorization": "Bearer your_token_here",
   }
   ```

### Issue: "OpenAI API key not found" or validation errors

**Cause:** Missing or invalid `.env` file.

**Solution:**
1. Create `.env` in the project root:
   ```env
   OPENAI_API_KEY=sk-...
   ```
2. Verify the key is valid at https://platform.openai.com/api-keys
3. Ensure no quotes around the key in `.env`

### Issue: "Connection timeout" errors

**Cause:** Slow network or API rate limiting.

**Solution:**
1. Increase `TIMEOUT` in the script (default 30 sec):
   ```python
   TIMEOUT = 60
   ```
2. Increase `PAUSE` between requests (default 1.5 sec):
   ```python
   PAUSE = 3.0
   ```

### Issue: Most tests fail on "Conciseness"

**Cause:** Chatbot replies are too long.

**Solution:**
1. Review the `SPACEY_V2_BEHAVIOUR.md` document for reply guidelines
2. Spacey should respond in **1–2 sentences**, not paragraphs
3. Space cards should appear below the text, not listed in the reply

### Issue: HTML report not opening

**Cause:** Browser may not open automatically, or file path has issues.

**Solution:**
1. Manually navigate to `spacey_deepeval_report.html` in the project folder
2. Right-click → Open with → Browser
3. Or check the console output for the file path

### Issue: Evaluation hangs or takes >5 minutes

**Cause:** Network latency, OpenAI rate limiting, or slow Spacey API.

**Solution:**
1. Run with `--dry-run` first to confirm config works
2. Try a subset: `python spacey_deepeval_v4.py --tags search`
3. Contact MillionSpaces support if Spacey API is consistently slow

---

## Integration with CI/CD

Example GitHub Actions workflow:

```yaml
name: Spacey Evaluation

on: [push, pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install deepeval requests python-dotenv
      - name: Run evaluation
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          echo "OPENAI_API_KEY=$OPENAI_API_KEY" > .env
          python spacey_deepeval_v4.py --json
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: eval-results
          path: spacey_deepeval_results*
```

---

## File Reference

| File | Purpose |
|------|---------|
| `spacey_deepeval_v4.py` | Main evaluation script |
| `SPACEY_V2_BEHAVIOUR.md` | Detailed chatbot behavior specification |
| `.env` | Environment variables (API keys) — **do not commit** |
| `spacey_deepeval_results.csv` | Evaluation results (CSV format) |
| `spacey_deepeval_report.html` | Evaluation report (interactive HTML) |
| `README.md` | This file |

---

## Support & Feedback

- **Questions?** Review `SPACEY_V2_BEHAVIOUR.md` for detailed product behavior.
- **Metric too strict/loose?** Adjust `PASS_THRESHOLD` in the script.
- **New test cases needed?** Add to `EVAL_CASES` list in the script.
- **DeepEval docs:** https://github.com/confident-ai/deepeval

---

**Last Updated:** June 2026  
**Version:** 4.0 (Spacey DeepEval)
