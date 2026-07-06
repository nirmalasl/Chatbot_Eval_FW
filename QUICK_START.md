# Spacey DeepEval — Quick Start Guide

Get up and running in **5 minutes**.

---

## Quick Facts

- **42 test cases** covering search, multi-turn, amenities, chip removal, and edge cases
- **7 core + custom metrics** for comprehensive evaluation
- **Multiple output formats**: console, CSV, HTML, JSON

## 1. Install (2 min)

```bash
pip install deepeval requests python-dotenv
```

## 2. Configure (2 min)

Create `.env` in the project folder:

```env
OPENAI_API_KEY=sk-your-key-here
```

Get a key at https://platform.openai.com/api-keys

## 3. Run (1 min)

```bash
# See all test cases (no API calls)
python spacey_deepeval_v4.py --dry-run

# Run full evaluation
python spacey_deepeval_v4.py

# Generate HTML report
python spacey_deepeval_v4.py --html
```

---

## Common Commands

| Command | Result |
|---------|--------|
| `python spacey_deepeval_v4.py` | Full evaluation, print results |
| `python spacey_deepeval_v4.py --html` | Full evaluation + HTML report |
| `python spacey_deepeval_v4.py --tags search multi-turn` | Only "search" and "multi-turn" tests |
| `python spacey_deepeval_v4.py --fail-fast` | Stop on first failure |
| `python spacey_deepeval_v4.py --dry-run` | Preview tests, no API calls |

---

## What Gets Tested?

✓ **Does Spacey find workspaces?** (search functionality)  
✓ **Does it remember context?** (multi-turn conversations)  
✓ **Does it handle filters?** (budget, date, location, capacity)  
✓ **Does it respond appropriately?** (tone, brevity, off-topic handling)  
✓ **Does it handle edge cases?** (no results, unsupported types, handoff)

---

## Results

After running, you'll see:
- **Pass/Fail** for each test
- **Metric scores** (0–1 scale)
- **Summary** — Pass rate %

Example:
```
Test E-01: meeting room in Colombo
  ✓ AnswerRelevancyMetric:  0.92
  ✓ Correctness:            0.88
  ✓ Conciseness:            0.95
  ✓ TaskCompletion:         0.87
  Result: PASS

Summary: 13 pass, 2 fail | Pass rate: 86.7%
```

---

## Output Files

| File | Format | When |
|------|--------|------|
| Console | Text | Always |
| `spacey_deepeval_results.csv` | CSV | With `--output` |
| `spacey_deepeval_report.html` | Interactive HTML | With `--html` |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 403 Forbidden | Add auth headers to script (see README.md) |
| API key error | Check `.env` file exists with valid key |
| Timeout | Increase `TIMEOUT` in script (default 30s) |
| Tests too slow | Run subset: `--tags search` |

---

## Next Steps

- Review full [README.md](README.md) for detailed options
- See [TEST_CASES.md](TEST_CASES.md) for all 15+ test cases
- Check [SPACEY_V2_BEHAVIOUR.md](SPACEY_V2_BEHAVIOUR.md) for product spec

**Questions?** See the main README or refer to the architecture doc.
