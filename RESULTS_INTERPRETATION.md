# Spacey DeepEval — Results Interpretation Guide

How to read, analyze, and act on evaluation results.

---

## Reading Console Output

### Sample Output

```
═══════════════════════════════════════════════════════════════════════════════
Spacey DeepEval — Results Summary
═══════════════════════════════════════════════════════════════════════════════

Test E-01: meeting room in Colombo
  Tags: search
  Metrics:
    ✓ AnswerRelevancyMetric:      0.92
    ✓ GEval (Correctness):        0.88
    ✓ GEval (Conciseness):        0.95
    ✓ TaskCompletionMetric:       0.87
  Result: PASS ✓

Test E-02: I need a space
  Tags: clarify
  Metrics:
    ✓ AnswerRelevancyMetric:      0.85
    ✗ GEval (Conciseness):        0.42
    ✓ GEval (Correctness):        0.79
  Result: FAIL ✗

───────────────────────────────────────────────────────────────────────────────
Test E-03: What types of spaces do you have?
  Tags: clarify
  Metrics:
    ✓ AnswerRelevancyMetric:      0.91
    ✓ GEval (Correctness):        0.88
    ✓ GEval (Conciseness):        0.76
  Result: PASS ✓

═══════════════════════════════════════════════════════════════════════════════
Summary: 13 PASS, 2 FAIL, 0 ERROR | Pass Rate: 86.7%
═══════════════════════════════════════════════════════════════════════════════
```

### Understanding the Output

| Element | Meaning |
|---------|---------|
| ✓ (checkmark) | Metric passed (score ≥ 0.5) |
| ✗ (X) | Metric failed (score < 0.5) |
| Score (e.g., 0.92) | Raw metric score (0–1 scale) |
| PASS | All metrics for this test ≥ 0.5 |
| FAIL | Any metric for this test < 0.5 |
| ERROR | Test crashed or couldn't evaluate |
| Pass Rate | (Passed / Total) × 100 |

---

## Interpreting Scores

### Per-Metric Scores

**General scale:**
- **0.75–1.0:** Excellent
- **0.5–0.74:** Acceptable
- **< 0.5:** Needs improvement

### Failing Metrics (< 0.5)

When a metric fails, it indicates a specific problem:

| Metric | Fails When | Action |
|--------|-----------|--------|
| **AnswerRelevancy** | Bot doesn't address the query | Review response text; ensure clarity |
| **Correctness** | Response doesn't match expected behavior | Compare expected vs actual; adjust test if needed |
| **Conciseness** | Reply too long or lists spaces in text | Trim response; move listing to cards |
| **TaskCompletion** | Bot didn't return results (search) or contact info (handoff) | Debug API response; check filtering |
| **TopicAdherence** | Bot engages with off-topic request | Retrain/improve off-topic detection |
| **KnowledgeRetention** | Bot forgets prior context | Check conversation history handling |
| **Empathy** | No-result response lacks empathy/alternatives | Add suggestions; improve tone |

### Borderline Scores (0.5–0.75)

Scores in this range pass but indicate room for improvement:

- **0.7–0.75:** Minor issues; acceptable
- **0.5–0.69:** Should improve before production

**Action:** Review failing metric details and plan improvements.

---

## CSV Results Deep Dive

### Opening the CSV

After running with `--output`, open `spacey_deepeval_results.csv` in Excel/Sheets:

| Column | Example | What It Is |
|--------|---------|-----------|
| `test_id` | E-01 | Test case ID |
| `tags` | search,multi-turn | Applied tags (comma-separated) |
| `query` | meeting room in Colombo | User query tested |
| `expected` | Should return results... | Expected behavior |
| `answer_relevancy` | 0.92 | Relevancy score |
| `correctness` | 0.88 | Correctness score |
| `conciseness` | 0.95 | Conciseness score |
| `task_completion` | 0.87 | TaskCompletion score (if applicable) |
| `knowledge_retention` | (empty) | KnowledgeRetention score (if multi-turn) |
| `topic_adherence` | (empty) | TopicAdherence score (if off-topic) |
| `empathy` | (empty) | Empathy score (if empty result) |
| `result` | PASS | Overall result |

### Quick Analysis in Excel

1. **Filter for FAIL:**
   - Data → Filter → Filter result column for FAIL
   - Shows all failing tests

2. **Sort by score:**
   - Click column header → Sort ascending
   - Shows lowest-scoring metrics first

3. **Identify weak areas:**
   - Column: `conciseness` sorted ascending
   - If many low scores → Bot is too verbose

4. **Track trends:**
   - Copy previous results CSV
   - Compare columns side-by-side
   - Track if improvements are working

### Example Analysis

```
Failing tests:
E-02: Conciseness 0.42 → Response too long
E-05: Correctness 0.48 → Budget filter not applied correctly
E-13: Empathy 0.35 → No alternatives offered for empty result

Top issues:
1. Conciseness (2 tests) — need shorter replies
2. Correctness (1 test) — filter logic issue
3. Empathy (1 test) — add fallback suggestions
```

---

## HTML Report Interpretation

### Opening the Report

After running with `--html`:
1. File: `spacey_deepeval_report.html`
2. Open in any browser
3. No internet needed (completely local)

### Dashboard Section

Shows high-level stats:
- **Pass Rate:** Percentage of passing tests
- **Total Tests:** Number of tests run
- **Passed / Failed / Errors:** Count breakdown
- **Charts:** Visual pass/fail distribution

### Test Details

Each test has a card showing:
- **Test ID & Query**
- **All metric scores** (colored: green ≥ 0.5, red < 0.5)
- **Result:** PASS or FAIL
- **Expected behavior** (expandable)
- **Actual response** (expandable)

### Metric Heatmap

Color-coded grid showing all scores at a glance:
- **Green:** 0.75–1.0 (excellent)
- **Yellow:** 0.5–0.74 (acceptable)
- **Red:** < 0.5 (fail)

**Use this to spot patterns:**
- Full red row? Test is fundamentally broken
- One red cell? Single metric issue
- Mostly yellow? Bot is borderline; improvement needed

---

## Common Issues & Solutions

### Issue: Many tests fail on "Conciseness"

**Symptom:** Multiple tests show Conciseness < 0.5

**Root cause:** Bot replies are too long or list spaces in text

**Solution:**
1. Review bot response format
2. Ensure replies are 1–2 sentences max
3. Move space listings to cards (UI layer)
4. Example:
   - ❌ Bad: "Here are meeting rooms: Room A (5000), Room B (4000)..."
   - ✓ Good: "Here are meeting rooms for you." [Cards below]

### Issue: "TaskCompletion" fails on search tests

**Symptom:** Search queries return low TaskCompletion scores

**Root cause:** Bot not returning cards or returning wrong cards

**Solution:**
1. Check API response format (expected JSON structure)
2. Verify search filters are applied correctly
3. Debug filter parsing logic
4. Ensure cards are being returned in the response

### Issue: "KnowledgeRetention" fails on multi-turn tests

**Symptom:** Multi-turn tests lose context between turns

**Root cause:** Conversation history not being passed or used

**Solution:**
1. Verify conversation history is being sent to Spacey API
2. Check bot's use of history in prompt/context
3. Ensure prior turns are retained in state
4. Add debug logging to see what history is sent

### Issue: "Empathy" fails on empty-result tests

**Symptom:** Empty-result tests show low Empathy scores

**Root cause:** Generic "no results" message without alternatives

**Solution:**
1. Add empathetic opening: "Sorry, I couldn't find..."
2. Suggest alternatives:
   - "Try Colombo?"
   - "Remove budget filter?"
   - "Search all Sri Lanka?"
3. Show quick-action buttons in UI

### Issue: Overall pass rate too low (< 70%)

**Symptom:** Many tests failing; pass rate 60% or lower

**Root cause:** Could be multiple issues or bot changed significantly

**Action plan:**
1. Run with `--html` to visualize patterns
2. Identify most common failing metrics
3. Fix top 3 issues first (highest impact)
4. Re-run to verify improvements
5. Iterate on next issues

---

## Comparing Results Over Time

### Tracking Pass Rate

1. **Save results each run:**
   ```bash
   # Include timestamp or version
   python spacey_deepeval_v4.py --output
   mv spacey_deepeval_results.csv results-2026-06-18.csv
   ```

2. **Compare in spreadsheet:**
   - Open Excel
   - Create summary sheet with columns:
     - Date
     - Total Tests
     - Passed
     - Failed
     - Pass Rate %
   - Plot Pass Rate over time

3. **Track by metric:**
   - Copy "answer_relevancy" column from each run
   - Average across all tests
   - Trend line shows if improving

### Example Trend

```
Date       | Pass Rate | Trend
-----------|-----------|-------
2026-06-15 | 60.0%     | ↗
2026-06-16 | 72.0%     | ↗
2026-06-17 | 81.0%     | ↗
2026-06-18 | 86.7%     | ↗ (good progress!)
```

---

## When to Stop / Deploy

### Definition of "Ready"

✓ **Green light criteria:**
- Pass Rate ≥ 90%
- No FAIL results on critical tests (search, multi-turn)
- No ERROR results
- All metrics > 0.6 (on average)

### Conditional Ready

✓ **Amber light:**
- Pass Rate 75–89%
- One or two minor fails (not critical path)
- Deploy with monitoring

❌ **Red light (do not deploy):**
- Pass Rate < 75%
- Critical path failures (search, context)
- Multiple ERROR results

---

## Sharing Results

### For Product / Management

Use HTML report:
```bash
python spacey_deepeval_v4.py --html
# Share: spacey_deepeval_report.html
```

**Advantages:**
- Visual, easy to understand
- No technical knowledge needed
- Interactive: can drill into details
- No setup required (opens in browser)

### For Engineering / Debugging

Use CSV:
```bash
python spacey_deepeval_v4.py --output
# Share: spacey_deepeval_results.csv
```

**Advantages:**
- Detailed data
- Easy to analyze programmatically
- Can be diffed between runs
- Suitable for regression testing

### For CI/CD

Use JSON:
```bash
python spacey_deepeval_v4.py --json
# Share: spacey_deepeval_results.json
```

**Advantages:**
- Machine-readable
- Can be parsed by scripts
- Integrates with CI/CD pipelines

---

## Advanced: Custom Analysis

### Example: Calculate by Tag

```python
import json

with open('spacey_deepeval_results.json') as f:
    results = json.load(f)

# Group by tag
tags_results = {}
for test in results['tests']:
    for tag in test['tags']:
        if tag not in tags_results:
            tags_results[tag] = {'pass': 0, 'fail': 0}
        
        if test['result'] == 'PASS':
            tags_results[tag]['pass'] += 1
        else:
            tags_results[tag]['fail'] += 1

# Print summary
for tag, counts in tags_results.items():
    total = counts['pass'] + counts['fail']
    rate = (counts['pass'] / total * 100) if total > 0 else 0
    print(f"{tag:15} {rate:.1f}% ({counts['pass']}/{total})")
```

### Example: Find Worst Metric

```python
import json

with open('spacey_deepeval_results.json') as f:
    results = json.load(f)

metrics = {}
for test in results['tests']:
    for metric_name, score in test['metrics'].items():
        if metric_name not in metrics:
            metrics[metric_name] = []
        metrics[metric_name].append(score)

# Print average score per metric
for metric, scores in sorted(metrics.items(), key=lambda x: sum(x[1])/len(x[1])):
    avg = sum(scores) / len(scores)
    print(f"{metric:30} {avg:.2f} (worst)")
```

---

## See Also

- [README.md](README.md) — Usage guide
- [METRICS_REFERENCE.md](METRICS_REFERENCE.md) — Metric explanations
- [TEST_CASES.md](TEST_CASES.md) — Test case reference
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Common errors

---

**Need help?** Review the relevant documentation or add `--fail-fast` flag to stop on first issue for faster debugging.
