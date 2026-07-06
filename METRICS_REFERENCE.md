# Spacey DeepEval — Metrics Reference

Deep dive into each evaluation metric and how it scores responses.

---

## Overview

**10 total metrics** used across all test cases:

### Core Metrics (Applied to Every Test)
| Metric | Type | Purpose | Scale |
|--------|------|---------|-------|
| AnswerRelevancyMetric | Core | Does reply address query? | 0–1 |
| GEval (Correctness) | Core | Does reply match expected? | 0–1 |
| GEval (Conciseness) | Core | Is reply appropriately brief? | 0–1 |

### Selective Metrics (Tag-Driven)
| Metric | Type | Purpose | Scale |
|--------|------|---------|-------|
| TaskCompletionMetric | Selective | Did bot complete task? | 0–1 |
| TopicAdherenceMetric | Selective | Does bot stay on-topic? | 0–1 |
| KnowledgeRetentionMetric | Selective | Does bot remember context? | 0–1 |
| GEval (Empathy) | Selective | Empathetic tone on empty results? | 0–1 |
| GEval (AmenityAccuracy) | Selective | Amenity filters applied correctly? | 0–1 |
| GEval (ChipRemoval) | Selective | Filter removal cleanness? | 0–1 |
| GEval (ModeLanguage) | Selective | Browse vs Availability language? | 0–1 |

---

## Core Metrics (Applied to Every Test)

### 1. AnswerRelevancyMetric

**What it measures:** Does the bot's response actually address the user's query?

**Scoring:**
- **1.0 (Perfect):** Response directly answers/addresses query with no fluff
- **0.75–0.99 (Good):** Addresses query clearly with minor tangents
- **0.5–0.74 (Okay):** Addresses query but with some irrelevant content
- **0.25–0.49 (Poor):** Partially addresses; significant irrelevant content
- **0.0 (Fail):** Doesn't address query at all

**Example:**

| Query | Response | Score | Why |
|-------|----------|-------|-----|
| "meeting room in Colombo" | "Here are meeting rooms in Colombo for you." | 0.95 | Direct, relevant |
| "meeting room in Colombo" | "Meeting rooms are important. Here are options in Colombo." | 0.80 | Relevant but with preamble |
| "meeting room in Colombo" | "Colombo is nice. I can help with offices." | 0.45 | Tangential; doesn't mention meeting rooms |
| "How's the weather?" | "Let me help you find a workspace." | 0.30 | Completely off-topic |

**LLM Prompt (conceptual):**
```
User: "meeting room in Colombo"
Bot: "Here are some meeting rooms in Colombo for you."

Does this response directly address the user's request?
Score 0–1.
```

---

### 2. GEval (Correctness)

**What it measures:** Does the response match the expected behavior for this test case?

**Scoring:**
- **1.0 (Perfect):** Response exactly matches expected outcome
- **0.75–0.99 (Good):** Response mostly correct; minor deviations acceptable
- **0.5–0.74 (Okay):** Response partially correct but missing key elements
- **0.25–0.49 (Poor):** Response partially correct but significant issues
- **0.0 (Fail):** Response doesn't match expected at all

**Example (E-02 test):**

| Response | Expected | Score | Why |
|----------|----------|-------|-----|
| "What type of space do you need?" | Should ask about type | 1.0 | Perfect match |
| "I can help. What kind of space?" | Should ask about type | 0.95 | Slightly informal but correct |
| "Meeting rooms? Photo studios?" | Should ask about type | 0.75 | Asks via suggestions; acceptable |
| "Here are all spaces." [shows cards] | Should ask about type | 0.15 | Wrong action; should ask first |
| "I don't know." | Should ask about type | 0.0 | No help; not asking |

**LLM Prompt (conceptual):**
```
Test case: "I need a space"
Expected: Should ask a clarifying question about the type of space needed.
Bot response: "What kind of space are you looking for?"

Does the response match the expected behavior? Score 0–1.
```

---

### 3. GEval (Conciseness)

**What it measures:** Is the response appropriately brief for Spacey's product requirements?

**Spacey rule:** Replies should be **1–2 sentences max**. Do NOT list all spaces in plain text.

**Scoring:**
- **1.0 (Perfect):** 1–2 sentences, no filler, no space listing
- **0.9–0.99 (Good):** 2 sentences, minimal filler
- **0.75–0.89 (Okay):** 2–3 sentences, some filler but acceptable
- **0.5–0.74 (Borderline):** 3–4 sentences or starts listing spaces in text
- **0.25–0.49 (Poor):** 4+ sentences or lists many spaces
- **0.0 (Fail):** Paragraph+ or exhaustive listing

**Example:**

| Response | Length | Score | Why |
|----------|--------|-------|-----|
| "Here are some meeting rooms in Colombo for you." | 1 sentence | 1.0 | Perfect |
| "Looking for meeting rooms in Colombo? I found some options for you. Check them out!" | 2 sentences | 0.95 | 2 sentences, concise |
| "Meeting rooms in Colombo. I can show you options. Here are the best ones. Check availability." | 4 sentences | 0.60 | Too long, starting to list |
| "Meeting rooms in Colombo: (1) Room A, (2) Room B, (3) Room C, (4) Room D..." | Lists in text | 0.20 | Violates no-listing rule |
| "Meeting rooms are spaces where people gather to discuss business. In Colombo, there are many such spaces. Let me show you the best ones. Our top picks are: Room A (5000 LKR), Room B (4000 LKR), Room C (3500 LKR)..." | Paragraph | 0.0 | Way too long |

**LLM Prompt (conceptual):**
```
Spacey must reply in 1–2 sentences. It should NOT list spaces in plain text.
Response: "Here are some meeting rooms in Colombo for you."

Is this response appropriately concise? Score 0–1.
```

**Note:** Space cards displayed below the text don't count toward "listing" — the text itself must be brief.

---

## Selective Metrics (Tag-Driven)

### 4. TaskCompletionMetric

**Applied when:** `"search"` or `"handoff"` in test tags

**What it measures:** Did the bot complete the requested task?

**For "search" tests:**
- Task = Return relevant space cards
- **1.0:** Correct cards returned
- **0.5:** Some relevant cards, but incomplete
- **0.0:** No cards or irrelevant cards

**For "handoff" tests:**
- Task = Offer human agent contact
- **1.0:** Contact info + offer to connect
- **0.5:** Mentions human agent but incomplete
- **0.0:** No handoff offered

**Example (E-01):**

| Response | Cards shown? | Correct type/location? | Score |
|----------|--------------|------------------------|-------|
| "Here are meeting rooms in Colombo." [Shows 5 Colombo meeting room cards] | Yes | Yes | 1.0 |
| "Here are some rooms." [Shows 3 Colombo meeting rooms + 2 private offices] | Yes | Mostly | 0.75 |
| "Let me search." [No cards, thinking state] | No | N/A | 0.3 |
| "Here are all spaces." [Shows 50 unrelated cards] | Yes | No | 0.1 |

---

### 5. TopicAdherenceMetric

**Applied when:** `"off-topic"` in test tags

**What it measures:** Does the bot stay on-topic (workspace booking) and avoid off-topic tangents?

**Scoring:**
- **1.0:** Politely redirects, doesn't engage with off-topic request
- **0.75:** Acknowledges question but redirects clearly
- **0.5:** Discusses off-topic but redirects at end
- **0.25:** Partially answers off-topic question
- **0.0:** Engages fully with off-topic request

**Example (E-11: "What is the weather?"):**

| Response | Score | Why |
|----------|-------|-----|
| "I'm here to help you find workspaces. What type of space are you looking for?" | 1.0 | Direct redirect, no engagement |
| "I don't answer weather questions, but I can help find spaces. What type?" | 0.95 | Brief acknowledgment, redirect |
| "The weather in Colombo is usually tropical. Anyway, looking for a workspace?" | 0.50 | Partially answers off-topic |
| "According to weather data, Colombo is 28°C today. Let me find workspaces for you." | 0.25 | Answers off-topic; then redirects |
| "The weather is 28°C, humid, chance of rain tomorrow. Have fun!" | 0.0 | Only answers off-topic |

---

### 6. KnowledgeRetentionMetric

**Applied when:** `"multi-turn"` in test tags

**What it measures:** Does the bot remember prior conversation context?

**Scoring:**
- **1.0:** Uses all prior context correctly
- **0.75:** Uses most context, minor omissions
- **0.5:** Uses some context but loses some threads
- **0.25:** Minimal context retention
- **0.0:** Ignores all prior context; treats as fresh query

**Example (E-09):**

Prior context:
1. User: "photo shoot"
2. Bot: "Here are photo studios."
3. User: "in Kandy"
4. Bot: "Here are photo studios in Kandy."
5. User: "under 8000" ← current query

| Response | Retains... | Score |
|----------|-----------|-------|
| Shows photo studios in Kandy under 8000 LKR | Type + Location + Budget | 1.0 |
| Shows photo studios under 8000 (all Sri Lanka) | Type + Budget, loses Location | 0.75 |
| Shows photo studios in Kandy (ignores budget) | Type + Location, loses Budget | 0.75 |
| Shows meeting rooms under 8000 | Budget, loses Type + Location | 0.25 |
| Shows random spaces (no context) | Nothing | 0.0 |

---

### 7. GEval (Empathy)

**Applied when:** `"empty"` in test tags

**What it measures:** Does the bot respond empathetically to empty results (no matches)?

**Scoring:**
- **1.0:** Empathetic message + constructive alternatives
- **0.9–0.99:** Empathetic + some alternatives
- **0.75–0.89:** Empathetic but alternatives weak
- **0.5–0.74:** Minimal empathy, few alternatives
- **0.25–0.49:** Cold "no results" message
- **0.0:** Rude or no response

**Example (E-13: "video shoot in Jaffna under 500"):**

| Response | Empathy | Alternatives | Score |
|----------|---------|--------------|-------|
| "Sorry, I couldn't find any video shoots in Jaffna under 500 LKR. Would you like to try Colombo, remove the budget cap, or search all Sri Lanka?" | High | Yes (3) | 1.0 |
| "No video shoots found. Try Colombo or remove budget filter." | Low | Yes (2) | 0.75 |
| "Sorry, no results for that criteria." | High | No | 0.60 |
| "No results." | None | None | 0.20 |
| "You're searching wrong." | Negative | No | 0.0 |

---

## Custom GEval Metrics

### 8. GEval (AmenityAccuracy)

**Applied when:** `"amenity"` in test tags

**What it measures:** Are amenity filters applied correctly?

**Example filters:**
- WiFi, air conditioning, parking, kitchen, lounge, etc.

**Scoring:**
- **1.0:** Correct amenities filtered; cards show only matching
- **0.75:** Mostly correct; 1–2 amenities missed
- **0.5:** Some correct; significant misses
- **0.25:** Very few correct
- **0.0:** No filtering applied

**Example (hypothetical):**

Query: "meeting room with WiFi and parking"

| Response | Filters | Score |
|----------|---------|-------|
| Shows meeting rooms, all have WiFi + parking | Correct | 1.0 |
| Shows meeting rooms, most have WiFi + parking | Mostly correct | 0.85 |
| Shows meeting rooms, only WiFi (missing parking) | Partial | 0.60 |
| Shows meeting rooms, no amenity filter | None | 0.0 |

---

### 9. GEval (ChipRemoval)

**Applied when:** `"chip-removal"` in test tags

**What it measures:** When user clicks ✕ on a filter chip, is it removed cleanly?

**Scenario:**
1. Search results show filter chips
2. User clicks ✕ on one chip
3. UI sends synthetic message to remove that filter
4. Bot searches without that filter

**Scoring:**
- **1.0:** Correct filter removed; others retained
- **0.75:** Filter removed; minor issues
- **0.5:** Filter removed but some context lost
- **0.25:** Filter partially removed
- **0.0:** Filter not removed or broke search

**Example:**

Initial search: "photo studio in Colombo, budget 5000"
Chips: [photo shoot] [📍 Colombo] [💰 ≤ 5000]

User clicks ✕ on budget chip → synthetic msg: "photo studio in Colombo without budget limit"

| Response | Budget removed? | Colombo retained? | Score |
|----------|-----------------|-------------------|-------|
| Shows photo studios in Colombo (no budget cap) | Yes | Yes | 1.0 |
| Shows photo studios (country-wide, no budget) | Yes | No | 0.75 |
| Shows photo studios in Colombo (budget still capped) | No | Yes | 0.25 |
| Clears all filters; shows everything | Yes | No | 0.25 |

---

### 10. GEval (ModeLanguage)

**Applied when:** `"browse-mode"` in test tags

**What it measures:** Uses correct language for Browse vs Availability mode?

| Mode | Without Date | With Date |
|------|--------------|-----------|
| **Browse** | "Spaces You May Like" | ❌ Should switch to Availability |
| **Availability** | ❌ Wrong | "Available Spaces", "Book Now", show slots |

**Scoring:**
- **1.0:** Correct mode language
- **0.75:** Mostly correct with minor wording issues
- **0.5:** Mode logic correct but language off
- **0.25:** Mixed modes or confusing language
- **0.0:** Wrong mode entirely

**Example (E-06):**

Query: "training room for 20 people on 08-07-2026" (WITH date)

| Response | Button | Section | Score |
|----------|--------|---------|-------|
| "Available spaces for you." [Book Now] [Available Spaces] | Book Now | Available Spaces | 1.0 |
| "Here are spaces for you." [View Details] [Spaces You May Like] | View Details | Browse | 0.0 |
| "Training rooms available." [View Details] [Spaces You May Like] | View Details | Browse | 0.1 |

---

## Passing Scores

**Default PASS_THRESHOLD:** 0.5

| Score Range | Grade | Status |
|-------------|-------|--------|
| 0.75–1.0 | A (Strong) | ✓ PASS |
| 0.5–0.74 | B (Okay) | ✓ PASS |
| < 0.5 | F (Fail) | ✗ FAIL |

**Test passes if ALL metrics ≥ 0.5**

If any single metric < 0.5 → entire test FAILS

---

## Adjusting Pass Threshold

**Default:** `PASS_THRESHOLD = 0.5`

To make tests stricter:
```python
PASS_THRESHOLD = 0.7  # Higher bar (A/B grades only)
```

To make tests more lenient:
```python
PASS_THRESHOLD = 0.4  # Lower bar (more forgiving)
```

**Recommendation:** Keep at 0.5 unless your product has strict SLA requirements.

---

## LLM Scoring Model

**Metrics are scored by:** `gpt-4o-mini` (configurable)

**Configuration:**
```python
EVAL_MODEL = "gpt-4o-mini"  # Default
# Options: gpt-4o-mini (fast, cheap), gpt-4-turbo (accurate), gpt-4 (best)
```

**Scoring flow:**
```
Query + Expected + Response
         ↓
    Send to GPT-4o-mini
         ↓
   Score each metric (0–1)
         ↓
   Return scores + reasoning
         ↓
   Compare to PASS_THRESHOLD
         ↓
   PASS or FAIL
```

---

## See Also

- [README.md](README.md) — Usage guide
- [TEST_CASES.md](TEST_CASES.md) — All test cases explained
- [ARCHITECTURE.md](ARCHITECTURE.md) — How metrics are assigned
- [SPACEY_V2_BEHAVIOUR.md](SPACEY_V2_BEHAVIOUR.md) — Product spec
