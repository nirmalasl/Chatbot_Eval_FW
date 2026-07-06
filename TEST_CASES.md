# Spacey DeepEval — Test Cases Reference

Complete documentation of all 42 evaluation test cases organized into 8 categories.

---

## Test Case Naming & Structure

**ID Format:** `E-NN` (E-01, E-02, etc.)

**Each case includes:**
- **ID:** Unique identifier
- **Query:** User message to evaluate
- **Expected:** What the correct response should accomplish
- **History:** Prior conversation turns (for multi-turn tests)
- **Tags:** Categorization for metric assignment

**Tags determine which metrics are applied** (see [README.md](README.md) > Evaluation Metrics).

---

## Category 1: Core Search (E-01 to E-04)

### E-01: Basic Space Search with Location

| Property | Value |
|----------|-------|
| **Query** | `meeting room in Colombo` |
| **Expected** | Should mention meeting rooms available in Colombo and offer relevant results. |
| **History** | (none) |
| **Tags** | `search` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion |

**What it tests:**
- Basic search functionality
- Location filtering
- Space type recognition
- Result card delivery

**Expected behavior:**
- Short 1–2 sentence reply acknowledging the query
- Space cards displayed below (not listed in text)
- Chips showing applied filters (if any)

---

### E-02: Clarification Needed (Space Type Missing)

| Property | Value |
|----------|-------|
| **Query** | `I need a space` |
| **Expected** | Should ask a clarifying question about the type of space needed — not return results yet. |
| **History** | (none) |
| **Tags** | `clarify` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness |

**What it tests:**
- Clarification handling
- Not forcing incomplete searches
- Conversational UX

**Expected behavior:**
- Ask "What type of space are you looking for?" or similar
- No space cards shown
- No chips

---

### E-03: List Supported Space Types

| Property | Value |
|----------|-------|
| **Query** | `What types of spaces do you have?` |
| **Expected** | Should list the 9 supported space types: meeting room, private office, photo studio, training room, video studio, individual desk, team office, virtual office, or interview room. |
| **History** | (none) |
| **Tags** | `clarify` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness |

**What it tests:**
- Space type enumeration
- Knowledge of supported types
- Helpful fallback when user is exploring

**Expected behavior:**
- List or reference the 9 types
- Brief format (not exhaustive)
- No cards (no specific search yet)

**Note:** The 9 types are:
1. Individual Workspace (coworking, hot desk)
2. Private Office
3. Virtual Office
4. Meeting Space (boardroom, meeting room)
5. Interview Room
6. Team Building
7. Training Room
8. Photo Shoot (photo studio)
9. Video Shoot (video studio)

---

### E-04: Location Only (Missing Space Type)

| Property | Value |
|----------|-------|
| **Query** | `Colombo` |
| **Expected** | Should ask what type of space the user is looking for — a city-only message is insufficient to search. |
| **History** | (none) |
| **Tags** | `clarify` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness |

**What it tests:**
- Location-only queries are insufficient
- Bot asks for required information
- Progressive search (type > location > filters)

**Expected behavior:**
- Ask "What type of space?" or similar
- No cards

---

## Category 2: Filters & Refinement (E-05 to E-07)

### E-05: Budget Filter (Price Cap)

| Property | Value |
|----------|-------|
| **Query** | `meeting room under 5000` |
| **Expected** | Should acknowledge the budget filter and return meeting rooms within 5000 LKR. |
| **History** | (none) |
| **Tags** | `search`, `amenity` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(AmenityAccuracy) |

**What it tests:**
- Budget filter parsing
- Price filtering correctness
- Filter acknowledgment in reply

**Expected behavior:**
- Acknowledge "under 5000" in text
- Show space cards with prices ≤ 5000 LKR
- Chip: `💰 ≤ LKR 5,000`

---

### E-06: Multi-Filter with Date (Availability Mode)

| Property | Value |
|----------|-------|
| **Query** | `training room for 20 people on {FUTURE_DATE}` |
| **Expected** | Should acknowledge the 20-person capacity and the specific date, switch to availability mode, and return results. The reply should NOT say "Spaces You May Like" — it should reflect availability mode. |
| **History** | (none) |
| **Tags** | `search`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(ModeLanguage) |

**What it tests:**
- Multiple filter handling (type, capacity, date)
- Browse → Availability mode switch
- Availability mode language ("Available Spaces", not "Spaces You May Like")
- Slot/seat display on cards

**Expected behavior:**
- Reply uses "Available" or "availability" language
- Cards show "Book Now" button (not "View Details")
- Cards show availability slots or seats (if API returns them)
- Chips: Type, Capacity, Date

---

### E-07: Pricing Question (Hedge)

| Property | Value |
|----------|-------|
| **Query** | `how much does coworking cost?` |
| **Expected** | Should provide a pricing hedge (prices vary) and show coworking / individual workspace cards country-wide. Should not give a single definitive price. |
| **History** | (none) |
| **Tags** | `search` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion |

**What it tests:**
- Pricing variability acknowledgment
- Hedge language ("prices vary", "typically", etc.)
- Coworking/individual workspace cards
- Country-wide search (no location restriction)

**Expected behavior:**
- Reply acknowledges price variability (no fixed price given)
- Shows coworking/individual workspace cards (all Sri Lanka)
- No chips for location (country-wide)

---

## Category 3: Multi-Turn Context (E-08 to E-09)

### E-08: Switch Space Type (Context Retention)

| Property | Value |
|----------|-------|
| **Query** | `actually private office` |
| **Expected** | Should switch context to private office search and return relevant results, potentially retaining the Colombo location from earlier in the conversation. |
| **History** | `[{"role": "user", "content": "meeting room in Colombo"}, {"role": "assistant", "content": "Here are some meeting rooms in Colombo for you."}]` |
| **Tags** | `search`, `multi-turn` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, KnowledgeRetentionMetric |

**What it tests:**
- Context switching within conversation
- Prior location retention (or not—both acceptable if intentional)
- Multi-turn understanding

**Expected behavior:**
- Recognize "actually private office" as a change request
- Show private office cards
- May keep Colombo filter or go country-wide (intent: switch type)

---

### E-09: Add Budget Filter (Multi-Filter Context)

| Property | Value |
|----------|-------|
| **Query** | `under 8000` |
| **Expected** | Should apply the budget filter to the ongoing photo-studio / Kandy search context and return results within the price limit — without asking for type or city again. |
| **History** | `[{"role": "user", "content": "photo shoot"}, {"role": "assistant", "content": "Here are some photo studios for you."}, {"role": "user", "content": "in Kandy"}, {"role": "assistant", "content": "Here are photo studios in Kandy."}]` |
| **Tags** | `search`, `multi-turn` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, KnowledgeRetentionMetric |

**What it tests:**
- Multi-filter accumulation
- Context memory over 4+ turns
- Budget filter applied to existing search context

**Expected behavior:**
- Recognize "under 8000" as budget addition (not new search)
- Apply to existing photo studio + Kandy context
- Show cards with price ≤ 8000 LKR
- Chips: Type (photo shoot), Location (Kandy), Budget (≤ 8000)

---

## Category 4: Human Handoff & Edge Cases (E-10 to E-15)

### E-10: Request Human Agent

| Property | Value |
|----------|-------|
| **Query** | `I need to speak to a real person` |
| **Expected** | Should offer to connect the user to a human agent and provide contact details (phone: 0117 811 811) or a handoff contact form. |
| **History** | (none) |
| **Tags** | `handoff` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletionMetric |

**What it tests:**
- Handoff capability detection
- Contact information accuracy
- Graceful escalation

**Expected behavior:**
- Acknowledge request
- Provide phone (0117 811 811) or contact form link
- UI may show "Talk to a human →" button

---

### E-11: Off-Topic Question (Weather)

| Property | Value |
|----------|-------|
| **Query** | `What is the weather in Colombo today?` |
| **Expected** | Should politely redirect the user back to workspace search and NOT attempt to answer the off-topic weather question. |
| **History** | (none) |
| **Tags** | `off-topic` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TopicAdherenceMetric |

**What it tests:**
- Off-topic detection
- Polite redirection
- Topic adherence

**Expected behavior:**
- Reply: "I'm here to help you find workspaces. What type of space are you looking for?"
- No weather answer
- No cards

---

### E-12: Greeting (Conversational Opener)

| Property | Value |
|----------|-------|
| **Query** | `Hi` |
| **Expected** | Should greet the user warmly and offer to help find a workspace — without immediately asking for lots of information. |
| **History** | (none) |
| **Tags** | `clarify` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness |

**What it tests:**
- Warm greeting tone
- Helpful opening without overwhelming
- Conversational UX

**Expected behavior:**
- Greeting: "Hi! I'm Spacey, how can I help?" or similar
- Soft ask: "What type of space are you looking for?"
- No cards, no pressure

---

### E-13: Empty Results (No Matches)

| Property | Value |
|----------|-------|
| **Query** | `video shoot in Jaffna under 500` |
| **Expected** | Should respond empathetically when no results match, and suggest alternatives such as trying Colombo, removing the budget cap, or broadening the search. Should NOT just say "no results" with no guidance. |
| **History** | (none) |
| **Tags** | `empty` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, GEval(Empathy) |

**What it tests:**
- No-result handling
- Empathetic tone
- Alternative suggestions
- Quick actions UI

**Expected behavior:**
- Empathetic message: "Sorry, I couldn't find any video shoots in Jaffna under 500 LKR."
- Quick action buttons:
  - "Try Colombo"
  - "Remove budget cap"
  - "Search all Sri Lanka"
- Chips remain (user can click ✕ to modify)

---

### E-14: Unsupported Space Type

| Property | Value |
|----------|-------|
| **Query** | `dedicated desk` |
| **Expected** | Should explain that "dedicated desk" is not a supported space type, list the 9 supported types, and suggest the closest alternative (e.g. individual workspace / coworking). |
| **History** | (none) |
| **Tags** | `clarify` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness |

**What it tests:**
- Unsupported type detection
- Helpful guidance to alternatives
- Type list reference

**Expected behavior:**
- Reply: "We don't have 'dedicated desk', but we do have Individual Workspaces / Coworking, which might work for you."
- No cards
- Link to list of 9 supported types

---

### E-15: Supported Type (Defer to User/Location)

| Property | Value |
|----------|-------|
| **Query** | `private office` |
| **Expected** | Should return private office listings or ask for a preferred city — NOT refuse or ask for the space type (user already stated it). |
| **History** | (none) |
| **Tags** | `search` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletionMetric |

**What it tests:**
- Type-only query handling
- No unnecessary re-asking
- Progressive search (can show country-wide first)

**Expected behavior:**
- Show private office cards (all Sri Lanka)
- Or ask softly: "Any city preference?" without questioning type
- No re-ask of type

---

## Category 5: Progressive Search & Modes (E-16+)

### E-16: Type-Only Query (No Location Demand)

| Property | Value |
|----------|-------|
| **Query** | `photo studio` |
| **Expected** | Should return photo studio cards for all of Sri Lanka WITHOUT asking for a city first. |
| **History** | (none) |
| **Tags** | `search` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletionMetric |

**What it tests:**
- Progressive search: type is sufficient
- No premature city demand
- Fast-path to results

**Expected behavior:**
- Show photo studio cards immediately (country-wide)
- No chip for location (not set)
- Soft ask: "Any preferred city?" (optional, not required)

---

## Adding New Test Cases

### Template

```python
EvalCase(
    "E-NN",  # Next available ID
    "user query here",
    "Expected behavior description.",
    history=[
        # Optional: prior turns
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
    ],
    tags={"tag1", "tag2"},  # Choose from existing tags
)
```

### Tag Selection Guide

| If test requires... | Use tag |
|---|---|
| Search results to be shown | `search` |
| Multi-turn context | `multi-turn` |
| Off-topic redirection | `off-topic` |
| Empty-result empathy | `empty` |
| Amenity filter logic | `amenity` |
| Chip removal handling | `chip-removal` |
| Browse vs Availability language | `browse-mode` |
| Just a question, no results | `clarify` |
| Human handoff | `handoff` |

---

## Running Specific Tests

**Run only search tests:**
```bash
python spacey_deepeval_v4.py --tags search
```

**Run multi-turn tests:**
```bash
python spacey_deepeval_v4.py --tags multi-turn
```

**Run multiple tags:**
```bash
python spacey_deepeval_v4.py --tags search multi-turn empty
```

**Run all tests:**
```bash
python spacey_deepeval_v4.py
```

---

## Interpreting Results

### Test PASSES if:
- **All** metrics score ≥ PASS_THRESHOLD (default 0.5)
- No metric fails

### Test FAILS if:
- **Any** metric scores < PASS_THRESHOLD
- Example: TaskCompletion = 0.42 → FAIL

### Metric Example Output:
```
Test E-01: meeting room in Colombo
  Metrics:
    ✓ AnswerRelevancyMetric:  0.92
    ✓ GEval (Correctness):    0.88
    ✓ GEval (Conciseness):    0.95
    ✓ TaskCompletionMetric:   0.87
  Result: PASS ✓
```

### E-17: Availability Mode Language (With Date)

| Property | Value |
|----------|-------|
| **Query** | `meeting room on {FUTURE_DATE}` |
| **Expected** | Should acknowledge the date, switch to availability mode, and return results. Response language should reflect availability ("available", "Book Now") rather than browse mode ("Spaces You May Like"). |
| **History** | (none) |
| **Tags** | `search`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(ModeLanguage) |

**What it tests:**
- Date-triggered availability mode
- Correct mode language usage
- Mode switch without location filter

**Expected behavior:**
- Reply uses "Available" or "availability" language
- Cards show "Book Now" button
- Chips show: Type, Date (no location)

---

### E-18: Country-Wide Query

| Property | Value |
|----------|-------|
| **Query** | `show me meeting rooms anywhere in Sri Lanka` |
| **Expected** | Should perform a country-wide meeting-room search across all of Sri Lanka without restricting to a specific city. |
| **History** | (none) |
| **Tags** | `search` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion |

**What it tests:**
- Explicit country-wide requests
- No city restriction
- "Anywhere" intent recognition

**Expected behavior:**
- Show meeting room cards (all Sri Lanka)
- No location chip
- Reply: "Here are meeting rooms across Sri Lanka."

---

### E-19: Unsupported Type (Event Space)

| Property | Value |
|----------|-------|
| **Query** | `I need an event space` |
| **Expected** | Should explain that "event space" is not one of the 9 supported types, list what IS available, and suggest the closest match (e.g. training room or meeting room). |
| **History** | (none) |
| **Tags** | `clarify` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness |

**What it tests:**
- Unsupported type detection
- Alternative suggestions (multiple options)
- Type list awareness

**Expected behavior:**
- Acknowledge request
- List 9 supported types
- Suggest: "Meeting Room or Training Room might work for an event."
- No cards

---

### E-20: Alias Mapping (Boardroom → Meeting Room)

| Property | Value |
|----------|-------|
| **Query** | `boardroom for 10 people in Colombo` |
| **Expected** | Should recognise "boardroom" as a synonym for "meeting room", apply the 10-person capacity filter, and return meeting rooms in Colombo. |
| **History** | (none) |
| **Tags** | `search` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion |

**What it tests:**
- Natural language alias mapping
- Capacity filter parsing
- Automatic type resolution

**Expected behavior:**
- Treat "boardroom" = "meeting room"
- Show meeting room cards in Colombo
- Apply 10-person capacity filter
- Chips: Type, Location, Capacity

---

### E-21: Alias Mapping (Hot Desk → Individual Workspace)

| Property | Value |
|----------|-------|
| **Query** | `hot desk in Colombo` |
| **Expected** | Should recognise "hot desk" as a synonym for individual workspace or coworking, and return relevant results in Colombo. |
| **History** | (none) |
| **Tags** | `search` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion |

**What it tests:**
- Coworking alias recognition
- Type normalization

**Expected behavior:**
- Treat "hot desk" = "individual workspace" or "coworking"
- Show individual workspace cards in Colombo
- Chips: Type, Location

---

### E-22: One-Shot Multi-Filter Query

| Property | Value |
|----------|-------|
| **Query** | `photo studio Colombo for 2 people under 10000 on {FUTURE_DATE}` |
| **Expected** | Should parse all filters from a single message — type (photo studio), city (Colombo), capacity (2 people), budget (≤ 10000 LKR), date ({FUTURE_DATE}) — and return availability-mode results matching all criteria. |
| **History** | (none) |
| **Tags** | `search`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(ModeLanguage) |

**What it tests:**
- Complex multi-filter parsing
- NLP robustness
- All filters applied simultaneously

**Expected behavior:**
- Recognize all 5 filters in one message
- Show photo studios in Colombo, ≤ 2 people, ≤ 10000 LKR, available on date
- Switch to availability mode (date present)
- Chips: Type, Location, Capacity, Budget, Date

---

### E-23: Mid-Chat Type Change (Location Retention)

| Property | Value |
|----------|-------|
| **Query** | `actually I want a private office` |
| **Expected** | Should switch the space type to private office while potentially retaining the Galle location from earlier context. Should NOT ask for location again. |
| **History** | `[{"role": "user", "content": "photo shoot in Galle"}, {"role": "assistant", "content": "Here are some photo studios in Galle for you."}]` |
| **Tags** | `search`, `multi-turn` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, KnowledgeRetentionMetric |

**What it tests:**
- Type change detection
- Context retention (location carry-over)
- No redundant questions

**Expected behavior:**
- Recognize type switch to private office
- Retain Galle filter (or ask softly, not as requirement)
- Show private office cards in Galle
- No re-ask of location

---

### E-24: Empty Results with Empathy (Specific City)

| Property | Value |
|----------|-------|
| **Query** | `interview room in Jaffna` |
| **Expected** | If no results are found, should respond empathetically and suggest broadening the search (e.g. "Try Colombo", remove location filter). Should not simply say "nothing found" with no guidance. |
| **History** | (none) |
| **Tags** | `search`, `empty` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, GEval(Empathy) |

**What it tests:**
- No-result handling
- Empathetic alternatives
- Quick action suggestions

**Expected behavior:**
- Empathetic reply: "I couldn't find any interview rooms in Jaffna..."
- Quick actions: "Try Colombo", "Search all Sri Lanka"
- Chips remain (user can modify filters)

---

### E-25: Multi-Turn Budget Refinement

| Property | Value |
|----------|-------|
| **Query** | `under 12000` |
| **Expected** | Should apply the budget filter to the existing private-office / Colombo context without asking for type or city again. Results should be filtered to ≤ LKR 12,000. |
| **History** | `[{"role": "user", "content": "private office in Colombo"}, {"role": "assistant", "content": "Here are some private offices in Colombo."}]` |
| **Tags** | `search`, `multi-turn` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, KnowledgeRetentionMetric |

**What it tests:**
- Budget filter addition to existing search
- Context memory
- No re-asking required info

**Expected behavior:**
- Add budget cap to private office + Colombo
- Show cards ≤ 12000 LKR
- Chips: Type, Location, Budget
- No re-ask of type/city

---

### E-26: Alternate Handoff Phrasing

| Property | Value |
|----------|-------|
| **Query** | `connect me to an agent` |
| **Expected** | Should recognise the human-handoff intent and provide a contact form or the phone number (0117 811 811). Should NOT continue showing space cards. |
| **History** | (none) |
| **Tags** | `handoff` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletionMetric |

**What it tests:**
- Handoff intent recognition (alternate phrasing)
- Contact info accuracy
- Action switch (no cards)

**Expected behavior:**
- Recognize "connect me to an agent" as handoff
- Provide: Phone (0117 811 811) or contact form
- UI: "Talk to a human" button
- No space cards

---

### E-27: Off-Topic (Joke Request)

| Property | Value |
|----------|-------|
| **Query** | `Tell me a joke` |
| **Expected** | Should politely decline and redirect the user to workspace search. Should NOT tell a joke. |
| **History** | (none) |
| **Tags** | `off-topic` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TopicAdherenceMetric |

**What it tests:**
- Off-topic request handling
- Polite decline
- Graceful redirection

**Expected behavior:**
- Reply: "I'm here to help you find workspaces, not tell jokes. What type of space are you looking for?"
- No joke told
- No cards

---

## Category 6: Amenity Filters (E-28 to E-35)

### E-28: Single Amenity (WiFi)

| Property | Value |
|----------|-------|
| **Query** | `Find me a space with WiFi` |
| **Expected** | Should apply the WiFi amenity filter and return only spaces that include WiFi. The reply should confirm the amenity filter is being applied, not return generic results. |
| **History** | (none) |
| **Tags** | `search`, `amenity`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(AmenityAccuracy), GEval(ModeLanguage) |

**What it tests:**
- Single amenity filter application
- Amenity confirmation in reply
- Browse mode (no date)

**Expected behavior:**
- Reply: "Here are spaces with WiFi for you."
- Show spaces with WiFi amenity only
- Chips: Amenity (WiFi)
- Browse mode language ("Spaces You May Like")

---

### E-29: Single Amenity (Video Conferencing)

| Property | Value |
|----------|-------|
| **Query** | `I need a space with Video Conferencing` |
| **Expected** | Should apply the Video Conferencing amenity filter and return spaces that include Video Conferencing. Should not confuse the amenity with a space type. |
| **History** | (none) |
| **Tags** | `search`, `amenity`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(AmenityAccuracy), GEval(ModeLanguage) |

**What it tests:**
- Amenity vs space type distinction
- Video Conferencing amenity parsing
- Correct filtering (not space type filtering)

**Expected behavior:**
- Treat as amenity filter (not space type)
- Show spaces with Video Conferencing
- Chips: Amenity (Video Conferencing)
- Browse mode

---

### E-30: Multi-Amenity (2 Amenities)

| Property | Value |
|----------|-------|
| **Query** | `Find a space with WiFi and a Projector` |
| **Expected** | Should apply BOTH the WiFi and Projector amenity filters. Only spaces that include both amenities should be in the results; spaces missing either are excluded. |
| **History** | (none) |
| **Tags** | `search`, `amenity`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(AmenityAccuracy), GEval(ModeLanguage) |

**What it tests:**
- Multi-amenity AND logic (both required)
- Correct intersection filtering

**Expected behavior:**
- Reply: "Here are spaces with WiFi and Projector for you."
- Show ONLY spaces with both WiFi AND Projector
- Chips: Amenity (WiFi), Amenity (Projector)

---

### E-31: Multi-Amenity (3 Amenities)

| Property | Value |
|----------|-------|
| **Query** | `I need a space that has Tea, Coffee, and Snacks` |
| **Expected** | Should apply Tea, Coffee, and Snacks amenity filters simultaneously. Results must include all three amenities. The reply should acknowledge all three filters. |
| **History** | (none) |
| **Tags** | `search`, `amenity`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(AmenityAccuracy), GEval(ModeLanguage) |

**What it tests:**
- 3+ amenity AND logic
- Complex multi-filter parsing

**Expected behavior:**
- Reply acknowledges all three: "Tea, Coffee, and Snacks"
- Show spaces with all three amenities
- Chips: Tea, Coffee, Snacks

---

### E-32: Natural Language Amenity Mapping

| Property | Value |
|----------|-------|
| **Query** | `I want a place where I can have lunch, charge my laptop, and use fast internet` |
| **Expected** | Should correctly map natural language descriptions to amenities: "have lunch" → Lunch, "charge my laptop" → Charging points, "fast internet" → WiFi. Results should match all three amenity filters. |
| **History** | (none) |
| **Tags** | `search`, `amenity`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(AmenityAccuracy), GEval(ModeLanguage) |

**What it tests:**
- Natural language → amenity mapping
- Inference and intent detection
- Multi-amenity with NL input

**Expected behavior:**
- Map: "lunch" → Lunch, "charge laptop" → Charging points, "fast internet" → WiFi
- Show spaces with all three
- Chips: Lunch, Charging points, WiFi
- Reply acknowledges mapping: "...with Lunch, Charging points, and WiFi"

---

### E-33: Amenity + Location Filter Combined

| Property | Value |
|----------|-------|
| **Query** | `Find a space in Colombo with Air Conditioning and WiFi` |
| **Expected** | Should apply BOTH the city filter (Colombo) AND amenity filters (Air Conditioning + WiFi). Results outside Colombo or missing either amenity must be excluded. |
| **History** | (none) |
| **Tags** | `search`, `amenity`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(AmenityAccuracy), GEval(ModeLanguage) |

**What it tests:**
- Location + amenity combination
- Intersection filtering (location AND amenities)

**Expected behavior:**
- Show spaces in Colombo with Air Conditioning AND WiFi
- Exclude: spaces outside Colombo, or missing AC, or missing WiFi
- Chips: Location (Colombo), Amenity (Air Conditioning), Amenity (WiFi)

---

### E-34: Multi-Turn Amenity Refinement

| Property | Value |
|----------|-------|
| **Query** | `Also add Breakfast to the filter` |
| **Expected** | Should retain the WiFi amenity from prior context AND add Breakfast as a new filter. Results must include both WiFi and Breakfast. Should NOT ask for the space type again. |
| **History** | `[{"role": "user", "content": "Find me a space with WiFi"}, {"role": "assistant", "content": "Here are spaces with WiFi for you."}]` |
| **Tags** | `search`, `amenity`, `multi-turn` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(AmenityAccuracy), KnowledgeRetentionMetric |

**What it tests:**
- Amenity accumulation over turns
- Context retention (WiFi + new Breakfast)
- No redundant questions

**Expected behavior:**
- Retain WiFi filter from prior turn
- Add Breakfast amenity
- Show spaces with BOTH WiFi and Breakfast
- Chips: WiFi, Breakfast
- No re-ask

---

### E-35: Impossible Amenity Combination (Empty Result)

| Property | Value |
|----------|-------|
| **Query** | `Find a space with Breast-feeding Area, Dressing Room, Smoking area, and Projector` |
| **Expected** | This unusual amenity combination will likely return zero results. Should respond empathetically and suggest alternatives such as removing some amenity filters, broadening the search, or trying Colombo. Should NOT just say "no results" with no guidance. |
| **History** | (none) |
| **Tags** | `amenity`, `empty` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, GEval(AmenityAccuracy), GEval(Empathy) |

**What it tests:**
- Empty result handling with amenities
- Empathetic suggestions
- Filter modification hints

**Expected behavior:**
- Empathetic reply: "Sorry, I couldn't find a space with all four of those amenities..."
- Suggestions: "Try removing one filter", "Try Colombo", "Broaden the search"
- Chips remain (user can modify)

---

## Category 7: Chip Removal (E-36 to E-38)

### E-36: Remove Budget Chip (Retain Type + Location)

| Property | Value |
|----------|-------|
| **Query** | `search without a budget limit` |
| **Expected** | This is a chip-removal message (user clicked ✕ on the budget chip). Should re-run the search for meeting rooms in Colombo WITHOUT a budget cap, retaining the space type (meeting room) and location (Colombo). Should NOT ask for type or city again. |
| **History** | `[{"role": "user", "content": "meeting room in Colombo under 8000"}, {"role": "assistant", "content": "Here are meeting rooms in Colombo under LKR 8,000."}]` |
| **Tags** | `search`, `chip-removal`, `multi-turn`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(ChipRemoval), GEval(ModeLanguage) |

**What it tests:**
- Budget chip removal
- Other filters retained (type, location)
- Context memory

**Expected behavior:**
- Remove budget cap
- Show meeting rooms in Colombo (no price limit)
- Chips: Type (meeting room), Location (Colombo) — budget removed
- No re-ask for type or city

---

### E-37: Remove Location Chip (Retain Budget, Expand to Sri Lanka)

| Property | Value |
|----------|-------|
| **Query** | `show photo shoot across Sri Lanka` |
| **Expected** | This is a chip-removal message (user clicked ✕ on the location chip). Should re-run the photo shoot search COUNTRY-WIDE (all Sri Lanka) retaining the budget cap (≤ LKR 10,000). Should NOT restrict to Colombo or any specific city. |
| **History** | `[{"role": "user", "content": "photo shoot in Colombo under 10000"}, {"role": "assistant", "content": "Here are photo studios in Colombo under LKR 10,000."}]` |
| **Tags** | `search`, `chip-removal`, `multi-turn`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(ChipRemoval), GEval(ModeLanguage) |

**What it tests:**
- Location chip removal
- Budget retained
- Country-wide search expansion

**Expected behavior:**
- Remove Colombo location filter
- Expand to all Sri Lanka
- Retain budget cap (≤ 10000)
- Show photo studios country-wide, ≤ 10000 LKR
- Chips: Type (photo shoot), Budget (≤ 10000) — location removed

---

### E-38: Remove Date Chip (Revert to Browse Mode)

| Property | Value |
|----------|-------|
| **Query** | `show meeting rooms in Colombo without a specific date` |
| **Expected** | This is a chip-removal message (user clicked ✕ on the date chip). Should re-run the meeting room / Colombo search in BROWSE MODE — response language should shift back to "Spaces You May Like" / "View Details" and must NOT use availability language ("Available Spaces", "Book Now", "available slots"). The date filter must be removed; other filters retained. |
| **History** | `[{"role": "user", "content": "meeting room in Colombo on {FUTURE_DATE}"}, {"role": "assistant", "content": "Here are available meeting rooms in Colombo."}]` |
| **Tags** | `search`, `chip-removal`, `multi-turn`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion, GEval(ChipRemoval), GEval(ModeLanguage) |

**What it tests:**
- Date chip removal
- Mode reversion (Availability → Browse)
- Browse mode language usage

**Expected behavior:**
- Remove date filter
- Revert to browse mode
- Use "Spaces You May Like", "View Details" language (NOT "Available Spaces", "Book Now")
- Hide availability slots/seats
- Chips: Type (meeting room), Location (Colombo) — date removed
- Button changes from "Book Now" to "View Details"

---

## Category 8: Missing Space Types (E-39 to E-42)

### E-39: Interview Room

| Property | Value |
|----------|-------|
| **Query** | `I need an interview room in Colombo` |
| **Expected** | Should recognise "interview room" as a supported space type and return interview room listings in Colombo. Should NOT ask for the space type again. |
| **History** | (none) |
| **Tags** | `search`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion |

**What it tests:**
- Interview room support
- Type recognition (rare type)
- Location filtering

**Expected behavior:**
- Recognize "interview room" as valid type
- Show interview room cards in Colombo
- Chips: Type (interview room), Location (Colombo)
- Browse mode

---

### E-40: Team Building

| Property | Value |
|----------|-------|
| **Query** | `team building space for 15 people` |
| **Expected** | Should recognise "team building" as a supported space type, apply the 15-person capacity filter, and return results. A country-wide search is acceptable if no city is specified. |
| **History** | (none) |
| **Tags** | `search`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion |

**What it tests:**
- Team building support
- Type recognition (uncommon type)
- Capacity filter application

**Expected behavior:**
- Recognize "team building" as valid type
- Apply 15-person capacity filter
- Show team building cards (country-wide or ask for city)
- Chips: Type (team building), Capacity (15+ people)

---

### E-41: Virtual Office

| Property | Value |
|----------|-------|
| **Query** | `virtual office` |
| **Expected** | Should recognise "virtual office" as a supported space type and return listings. May ask for preferred city or show country-wide results — both are acceptable. Should NOT confuse it with a physical private office. |
| **History** | (none) |
| **Tags** | `search`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion |

**What it tests:**
- Virtual office support
- Non-physical space type handling
- Distinction from private office

**Expected behavior:**
- Recognize "virtual office" as valid (non-physical) type
- Show virtual office cards (country-wide OK)
- Do NOT treat as "private office"
- Chips: Type (virtual office)

---

### E-42: Alias Mapping (Video Studio → Video Shoot)

| Property | Value |
|----------|-------|
| **Query** | `video studio in Colombo` |
| **Expected** | Should recognise "video studio" as an alias for the "Video Shoot" space type and return video shoot spaces in Colombo. Should NOT treat this as an unsupported type. |
| **History** | (none) |
| **Tags** | `search`, `browse-mode` |
| **Metrics** | AnswerRelevancy, Correctness, Conciseness, TaskCompletion |

**What it tests:**
- Alias mapping (video studio ↔ video shoot)
- Type normalization
- No false unsupported type detection

**Expected behavior:**
- Map "video studio" → "Video Shoot"
- Show video shoot cards in Colombo
- Chips: Type (Video Shoot), Location (Colombo)
- Browse mode

---

## See Also

- [README.md](README.md) — Usage & Configuration
- [ARCHITECTURE.md](ARCHITECTURE.md) — How the framework works
- [SPACEY_V2_BEHAVIOUR.md](SPACEY_V2_BEHAVIOUR.md) — Product specification
- [METRICS_REFERENCE.md](METRICS_REFERENCE.md) — Detailed metric explanations
