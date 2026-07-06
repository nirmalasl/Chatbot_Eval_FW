#!/usr/bin/env python3
"""
Spacey — DeepEval Chatbot Evaluation Script  (v4)

Evaluates chatbot response quality using deepeval metrics, assigned
per-case based on what each test is actually probing:

  Core (every case)
  ─────────────────
  • AnswerRelevancyMetric — does the reply address the user's query?
  • GEval (Correctness)   — does the reply match the expected behaviour?
  • GEval (Conciseness)   — is the reply appropriately short (1–2 sentences)?
                            Spacey must NOT list all spaces in plain text.

  Selective (tag-driven)
  ──────────────────────
  • TaskCompletionMetric      [tag: search]        — did the bot complete the search task?
  • TopicAdherenceMetric      [tag: off-topic]     — does the bot stay on workspace booking?
  • KnowledgeRetentionMetric  [tag: multi-turn]    — does the bot remember prior-turn context?
  • GEval (Empathy)           [tag: empty]         — empathetic tone on zero-result cases?
  • GEval (AmenityAccuracy)   [tag: amenity]       — did the bot apply the correct amenity filter?
  • GEval (ChipRemoval)       [tag: chip-removal]  — did the bot drop the right filter, keep others?
  • GEval (ModeLanguage)      [tag: browse-mode]   — browse vs availability mode language correct?

Tags reference
──────────────
  search       — bot should return space results
  clarify      — bot should ask a question, not return results
  off-topic    — bot should redirect to workspace booking
  multi-turn   — conversation has prior history; context must carry over
  handoff      — bot should trigger human-agent / contact form
  empty        — expect no results; bot should respond with empathy + alternatives
  amenity      — query involves one or more amenity filters (MIL-347 coverage)
  chip-removal — synthetic message produced by ✕ chip click; filter must be removed cleanly
  browse-mode  — response must use browse-mode language (no "Available" if no date given)

Prerequisites:
  pip install deepeval requests python-dotenv

Auth:
  1. Spacey endpoint: add Cookie/Authorization to AUTH_HEADERS if you get 403s.
  2. OpenAI API key:  create a .env file with OPENAI_API_KEY=sk-...

Usage:
  python spacey_deepeval_v4.py              # full evaluation
  python spacey_deepeval_v4.py --dry-run    # print dataset, skip API calls
  python spacey_deepeval_v4.py --output     # also save results to CSV
  python spacey_deepeval_v4.py --html       # also save results to HTML report
  python spacey_deepeval_v4.py --json       # also save results to JSON
  python spacey_deepeval_v4.py --fail-fast  # stop on first metric failure
  python spacey_deepeval_v4.py --tags search amenity chip-removal   # run specific tags
"""

import argparse
import csv
import datetime
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────

BASE_URL       = "https://api-prod-ecs.millionspaces.com/api/search/agent/chat"
TIMEOUT        = 30       # seconds per request
PAUSE          = 1.5      # delay between API calls to avoid rate limiting
MAX_RETRIES    = 2        # retries on 5xx / timeout
FUTURE_DATE    = (datetime.date.today() + datetime.timedelta(days=20)).strftime("%d-%m-%Y")

# ── DeepEval evaluation config ────────────────────────────────────────────────
EVAL_MODEL     = "gpt-4o-mini"   # LLM used by all DeepEval metrics
PASS_THRESHOLD = 0.5              # minimum score for a metric to be considered passing

# Add session headers here if the endpoint returns 403
AUTH_HEADERS: dict = {
    # "Cookie":        "your_session_cookie_here",
    # "Authorization": "Bearer your_token_here",
}

BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept":       "application/json",
    "Origin":       "https://millionspaces.com",
    "Referer":      "https://millionspaces.com/Sri-Lanka",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    **AUTH_HEADERS,
}

# ─── COLOURS ─────────────────────────────────────────────────────────────────

GREEN  = "\033[92m"; YELLOW = "\033[93m"; CYAN = "\033[96m"
BOLD   = "\033[1m";  DIM    = "\033[2m";  RESET = "\033[0m"

def bold(s):   return f"{BOLD}{s}{RESET}"
def dim(s):    return f"{DIM}{s}{RESET}"
def cyan(s):   return f"{CYAN}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def green(s):  return f"{GREEN}{s}{RESET}"

# ─── EVAL DATASET ─────────────────────────────────────────────────────────────
#
# Tags drive which metrics are applied to each case:
#   "search"      → + TaskCompletionMetric
#   "off-topic"   → + TopicAdherenceMetric
#   "multi-turn"  → + KnowledgeRetentionMetric (ConversationalTestCase)
#   "empty"       → + GEval(Empathy)
#   "clarify"     → core only  (bot should ask, not answer)
#   "handoff"     → + TaskCompletionMetric
#
# All cases also get: AnswerRelevancy + GEval(Correctness) + GEval(Conciseness)

@dataclass
class EvalCase:
    id:       str
    query:    str
    expected: str
    history:  list  = field(default_factory=list)
    tags:     set   = field(default_factory=set)   # e.g. {"search", "multi-turn"}

    def has_tag(self, *t) -> bool:
        return bool(self.tags.intersection(t))


EVAL_CASES: list[EvalCase] = [

    # ── Core search ─────────────────────────────────────────────────────────
    EvalCase(
        "E-01", "meeting room in Colombo",
        "Should mention meeting rooms available in Colombo and offer relevant results.",
        tags={"search"},
    ),
    EvalCase(
        "E-02", "I need a space",
        "Should ask a clarifying question about the type of space needed — not return results yet.",
        tags={"clarify"},
    ),
    EvalCase(
        "E-03", "What types of spaces do you have?",
        "Should list the 9 supported space types: meeting room, private office, photo studio, "
        "training room, video studio, individual desk, team office, virtual office, or interview room.",
        tags={"clarify"},
    ),
    EvalCase(
        "E-04", "Colombo",
        "Should ask what type of space the user is looking for — a city-only message is insufficient to search.",
        tags={"clarify"},
    ),

    # ── Filters ─────────────────────────────────────────────────────────────
    EvalCase(
        "E-05", "meeting room under 5000",
        "Should acknowledge the budget filter and return meeting rooms within 5000 LKR.",
        tags={"search"},
    ),
    EvalCase(
        "E-06", f"training room for 20 people on {FUTURE_DATE}",
        "Should acknowledge the 20-person capacity and the specific date, switch to availability mode, "
        "and return results. The reply should NOT say 'Spaces You May Like' — it should reflect availability mode.",
        tags={"search"},
    ),
    EvalCase(
        "E-07", "how much does coworking cost?",
        "Should provide a pricing hedge (prices vary) and show coworking / individual workspace cards "
        "country-wide. Should not give a single definitive price.",
        tags={"search"},
    ),

    # ── Multi-turn ──────────────────────────────────────────────────────────
    EvalCase(
        "E-08", "actually private office",
        "Should switch context to private office search and return relevant results, "
        "potentially retaining the Colombo location from earlier in the conversation.",
        history=[
            {"role": "user",      "content": "meeting room in Colombo"},
            {"role": "assistant", "content": "Here are some meeting rooms in Colombo for you."},
        ],
        tags={"search", "multi-turn"},
    ),
    EvalCase(
        "E-09", "under 8000",
        "Should apply the budget filter to the ongoing photo-studio / Kandy search context "
        "and return results within the price limit — without asking for type or city again.",
        history=[
            {"role": "user",      "content": "photo shoot"},
            {"role": "assistant", "content": "Here are some photo studios for you."},
            {"role": "user",      "content": "in Kandy"},
            {"role": "assistant", "content": "Here are photo studios in Kandy."},
        ],
        tags={"search", "multi-turn"},
    ),

    # ── Human handoff ───────────────────────────────────────────────────────
    EvalCase(
        "E-10", "I need to speak to a real person",
        "Should offer to connect the user to a human agent and provide contact details "
        "(phone: 0117 811 811) or a handoff contact form.",
        tags={"handoff"},
    ),

    # ── Edge cases ──────────────────────────────────────────────────────────
    EvalCase(
        "E-11", "What is the weather in Colombo today?",
        "Should politely redirect the user back to workspace search and NOT attempt to answer "
        "the off-topic weather question.",
        tags={"off-topic"},
    ),
    EvalCase(
        "E-12", "Hi",
        "Should greet the user warmly and offer to help find a workspace — "
        "without immediately asking for lots of information.",
        tags={"clarify"},
    ),
    EvalCase(
        "E-13", "video shoot in Jaffna under 500",
        "Should respond empathetically when no results match, and suggest alternatives "
        "such as trying Colombo, removing the budget cap, or broadening the search. "
        "Should NOT just say 'no results' with no guidance.",
        tags={"empty"},
    ),
    EvalCase(
        "E-14", "dedicated desk",
        "Should explain that 'dedicated desk' is not a supported space type, "
        "list the 9 supported types, and suggest the closest alternative "
        "(e.g. individual workspace / coworking).",
        tags={"clarify"},
    ),
    EvalCase(
        "E-15", "private office",
        "Should return private office listings or ask for a preferred city — "
        "NOT refuse or ask for the space type (user already stated it).",
        tags={"search"},
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # NEW CASES — gaps identified from SPACEY_V2_BEHAVIOUR.md
    # ═══════════════════════════════════════════════════════════════════════

    # §4.1 Progressive search — type-only should return cards without demanding a city
    EvalCase(
        "E-16", "photo studio",
        "Should return photo studio cards for all of Sri Lanka WITHOUT asking for a city first. "
        "Per the progressive search spec, the first search can be country-wide.",
        tags={"search"},
    ),

    # §4.2 Availability mode language — date triggers mode switch
    EvalCase(
        "E-17", f"meeting room on {FUTURE_DATE}",
        f"Should acknowledge the date ({FUTURE_DATE}), switch to availability mode, "
        "and return results. The response language should reflect availability "
        "(e.g. 'available', 'Book Now') rather than browse mode ('Spaces You May Like').",
        tags={"search"},
    ),

    # §4.12 Country-wide / "anywhere" query
    EvalCase(
        "E-18", "show me meeting rooms anywhere in Sri Lanka",
        "Should perform a country-wide meeting-room search across all of Sri Lanka "
        "without restricting to a specific city.",
        tags={"search"},
    ),

    # §3 Unsupported space type — not in the 9 supported types
    EvalCase(
        "E-19", "I need an event space",
        "Should explain that 'event space' is not one of the 9 supported types, "
        "list what IS available (meeting room, training room, etc.), "
        "and suggest the closest match (e.g. training room or meeting room).",
        tags={"clarify"},
    ),

    # §3 Alternate naming — "boardroom" should map to meeting room
    EvalCase(
        "E-20", "boardroom for 10 people in Colombo",
        "Should recognise 'boardroom' as a synonym for 'meeting room', "
        "apply the 10-person capacity filter, and return meeting rooms in Colombo.",
        tags={"search"},
    ),

    # §3 Alternate naming — "hot desk" should map to individual workspace / coworking
    EvalCase(
        "E-21", "hot desk in Colombo",
        "Should recognise 'hot desk' as a synonym for individual workspace or coworking, "
        "and return relevant results in Colombo.",
        tags={"search"},
    ),

    # §4.1 One-shot full query with all filters at once
    EvalCase(
        "E-22", f"photo studio Colombo for 2 people under 10000 on {FUTURE_DATE}",
        f"Should parse all filters from a single message — type (photo studio), "
        f"city (Colombo), capacity (2 people), budget (≤ 10000 LKR), date ({FUTURE_DATE}) — "
        "and return availability-mode results matching all criteria.",
        tags={"search"},
    ),

    # §4.12 Mid-chat type change — location should carry over
    EvalCase(
        "E-23", "actually I want a private office",
        "Should switch the space type to private office while potentially retaining "
        "the Galle location from earlier context. Should NOT ask for location again.",
        history=[
            {"role": "user",      "content": "photo shoot in Galle"},
            {"role": "assistant", "content": "Here are some photo studios in Galle for you."},
        ],
        tags={"search", "multi-turn"},
    ),

    # §4.7 Empty results in a specific city — empathy + alternatives
    EvalCase(
        "E-24", "interview room in Jaffna",
        "If no results are found, should respond empathetically and suggest broadening "
        "the search (e.g. 'Try Colombo', remove location filter). "
        "Should not simply say 'nothing found' with no guidance.",
        tags={"search", "empty"},
    ),

    # §4.3 Multi-turn filter refinement — budget added to existing search
    EvalCase(
        "E-25", "under 12000",
        "Should apply the budget filter to the existing private-office / Colombo context "
        "without asking for type or city again. "
        "Results should be filtered to ≤ LKR 12,000.",
        history=[
            {"role": "user",      "content": "private office in Colombo"},
            {"role": "assistant", "content": "Here are some private offices in Colombo."},
        ],
        tags={"search", "multi-turn"},
    ),

    # §4.9 Human handoff — alternate trigger phrasing
    EvalCase(
        "E-26", "connect me to an agent",
        "Should recognise the human-handoff intent and provide a contact form or "
        "the phone number (0117 811 811). Should NOT continue showing space cards.",
        tags={"handoff"},
    ),

    # §4.12 Off-topic — joke / unrelated request
    EvalCase(
        "E-27", "Tell me a joke",
        "Should politely decline and redirect the user to workspace search. "
        "Should NOT tell a joke.",
        tags={"off-topic"},
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # MIL-347 AMENITY COVERAGE — gaps from amenity-search test plan
    # ═══════════════════════════════════════════════════════════════════════

    # Single amenity — WiFi (most common; baseline amenity test)
    EvalCase(
        "E-28", "Find me a space with WiFi",
        "Should apply the WiFi amenity filter and return only spaces that include WiFi. "
        "The reply should confirm the amenity filter is being applied, not return generic results.",
        tags={"search", "amenity", "browse-mode"},
    ),

    # Single amenity — Video Conferencing (AV-heavy; distinct from space type)
    EvalCase(
        "E-29", "I need a space with Video Conferencing",
        "Should apply the Video Conferencing amenity filter and return spaces that include "
        "Video Conferencing. Should not confuse the amenity with a space type.",
        tags={"search", "amenity", "browse-mode"},
    ),

    # Multi-amenity — two amenities (TC-MIL347-22 equivalent)
    EvalCase(
        "E-30", "Find a space with WiFi and a Projector",
        "Should apply BOTH the WiFi and Projector amenity filters. "
        "Only spaces that include both amenities should be in the results; "
        "spaces missing either are excluded.",
        tags={"search", "amenity", "browse-mode"},
    ),

    # Multi-amenity — three amenities (TC-MIL347-23 equivalent)
    EvalCase(
        "E-31", "I need a space that has Tea, Coffee, and Snacks",
        "Should apply Tea, Coffee, and Snacks amenity filters simultaneously. "
        "Results must include all three amenities. The reply should acknowledge all three filters.",
        tags={"search", "amenity", "browse-mode"},
    ),

    # NL-to-amenity mapping — TC-MIL347-27 equivalent
    EvalCase(
        "E-32",
        "I want a place where I can have lunch, charge my laptop, and use fast internet",
        "Should correctly map natural language descriptions to amenities: "
        "'have lunch' → Lunch, 'charge my laptop' → Charging points, "
        "'fast internet' → WiFi. Results should match all three amenity filters.",
        tags={"search", "amenity", "browse-mode"},
    ),

    # Amenity + location filter combined — TC-MIL347-28 equivalent
    EvalCase(
        "E-33", "Find a space in Colombo with Air Conditioning and WiFi",
        "Should apply BOTH the city filter (Colombo) AND amenity filters "
        "(Air Conditioning + WiFi). Results outside Colombo or missing either amenity must be excluded.",
        tags={"search", "amenity", "browse-mode"},
    ),

    # Multi-turn amenity refinement — TC-MIL347-30 equivalent
    EvalCase(
        "E-34", "Also add Breakfast to the filter",
        "Should retain the WiFi amenity from prior context AND add Breakfast as a new filter. "
        "Results must include both WiFi and Breakfast. Should NOT ask for the space type again.",
        history=[
            {"role": "user",      "content": "Find me a space with WiFi"},
            {"role": "assistant", "content": "Here are spaces with WiFi for you."},
        ],
        tags={"search", "amenity", "multi-turn"},
    ),

    # Impossible amenity combination → empty results — TC-MIL347-26 equivalent
    EvalCase(
        "E-35",
        "Find a space with Breast-feeding Area, Dressing Room, Smoking area, and Projector",
        "This unusual amenity combination will likely return zero results. "
        "Should respond empathetically and suggest alternatives such as removing some amenity "
        "filters, broadening the search, or trying Colombo. "
        "Should NOT just say 'no results' with no guidance.",
        tags={"amenity", "empty"},
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # §4.3 CHIP REMOVAL — synthetic messages produced by ✕ chip clicks
    # ═══════════════════════════════════════════════════════════════════════

    # Remove budget chip — agent must retain type + location, drop budget cap
    EvalCase(
        "E-36", "search without a budget limit",
        "This is a chip-removal message (user clicked ✕ on the budget chip). "
        "Should re-run the search for meeting rooms in Colombo WITHOUT a budget cap, "
        "retaining the space type (meeting room) and location (Colombo). "
        "Should NOT ask for type or city again.",
        history=[
            {"role": "user",      "content": "meeting room in Colombo under 8000"},
            {"role": "assistant", "content": "Here are meeting rooms in Colombo under LKR 8,000."},
        ],
        tags={"search", "chip-removal", "multi-turn", "browse-mode"},
    ),

    # Remove location chip — agent must expand search to Sri Lanka, keep type + budget
    EvalCase(
        "E-37", "show photo shoot across Sri Lanka",
        "This is a chip-removal message (user clicked ✕ on the location chip). "
        "Should re-run the photo shoot search COUNTRY-WIDE (all Sri Lanka) "
        "retaining the budget cap (≤ LKR 10,000). "
        "Should NOT restrict to Colombo or any specific city.",
        history=[
            {"role": "user",      "content": "photo shoot in Colombo under 10000"},
            {"role": "assistant", "content": "Here are photo studios in Colombo under LKR 10,000."},
        ],
        tags={"search", "chip-removal", "multi-turn", "browse-mode"},
    ),

    # Remove date chip — agent must return to browse mode (no "Available Spaces")
    EvalCase(
        "E-38", f"show meeting rooms in Colombo without a specific date",
        "This is a chip-removal message (user clicked ✕ on the date chip). "
        "Should re-run the meeting room / Colombo search in BROWSE MODE — "
        "response language should shift back to 'Spaces You May Like' / 'View Details' "
        "and must NOT use availability language ('Available Spaces', 'Book Now', 'available slots'). "
        "The date filter must be removed; other filters retained.",
        history=[
            {"role": "user",      "content": f"meeting room in Colombo on {FUTURE_DATE}"},
            {"role": "assistant", "content": "Here are available meeting rooms in Colombo."},
        ],
        tags={"search", "chip-removal", "multi-turn", "browse-mode"},
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # §3 MISSING SPACE TYPES — Interview Room, Team Building, Virtual Office
    # ═══════════════════════════════════════════════════════════════════════

    # Interview Room — distinct supported type rarely tested
    EvalCase(
        "E-39", "I need an interview room in Colombo",
        "Should recognise 'interview room' as a supported space type and return "
        "interview room listings in Colombo. Should NOT ask for the space type again.",
        tags={"search", "browse-mode"},
    ),

    # Team Building — supported type that's easy to miss
    EvalCase(
        "E-40", "team building space for 15 people",
        "Should recognise 'team building' as a supported space type, "
        "apply the 15-person capacity filter, and return results. "
        "A country-wide search is acceptable if no city is specified.",
        tags={"search", "browse-mode"},
    ),

    # Virtual Office — unique non-physical type
    EvalCase(
        "E-41", "virtual office",
        "Should recognise 'virtual office' as a supported space type and return listings. "
        "May ask for preferred city or show country-wide results — both are acceptable. "
        "Should NOT confuse it with a physical private office.",
        tags={"search", "browse-mode"},
    ),

    # Alias mapping — "video studio" should resolve to Video Shoot space type
    EvalCase(
        "E-42", "video studio in Colombo",
        "Should recognise 'video studio' as an alias for the 'Video Shoot' space type "
        "and return video shoot spaces in Colombo. "
        "Should NOT treat this as an unsupported type.",
        tags={"search", "browse-mode"},
    ),
]

# ─── HTTP LAYER ──────────────────────────────────────────────────────────────

_CANDIDATE_SHAPES = [
    lambda msg, hist: {"message": msg, "history": hist},
    lambda msg, hist: {"message": msg, "history": hist, "country": "LK"},
    lambda msg, hist: {"query":   msg, "history": hist},
    lambda msg, hist: {"messages": hist + [{"role": "user", "content": msg}]},
]
_working_shape_idx: Optional[int] = None


def post_raw(payload: dict) -> tuple[int, dict]:
    """POST to the Spacey API with retry on transient errors."""
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            r = requests.post(BASE_URL, json=payload, headers=BASE_HEADERS, timeout=TIMEOUT)
            try:
                body = r.json()
            except Exception:
                body = {"_raw": r.text[:500]}
            if r.status_code in (429, 500, 502, 503) and attempt <= MAX_RETRIES:
                time.sleep(attempt * 2)
                continue
            return r.status_code, body
        except requests.exceptions.Timeout:
            if attempt <= MAX_RETRIES:
                time.sleep(attempt * 2)
                continue
            return 0, {"error": "timeout"}
        except requests.exceptions.RequestException as exc:
            if attempt <= MAX_RETRIES:
                time.sleep(attempt * 2)
                continue
            return 0, {"error": str(exc)}
    return 0, {"error": "max retries exceeded"}


def post(message: str, history: list) -> tuple[int, dict]:
    """Auto-detect the working payload shape, then reuse it for every call."""
    global _working_shape_idx
    if _working_shape_idx is not None:
        return post_raw(_CANDIDATE_SHAPES[_working_shape_idx](message, history))
    for i, shape_fn in enumerate(_CANDIDATE_SHAPES):
        payload = shape_fn(message, history)
        status, body = post_raw(payload)
        if status not in (400, 405, 422):
            _working_shape_idx = i
            print(dim(f"  [schema] Using payload shape #{i+1}: {list(payload.keys())}  HTTP {status}"))
            return status, body
    return post_raw(_CANDIDATE_SHAPES[-1](message, history))


def extract_reply(body: dict) -> str:
    """Pull the bot's reply text from whatever shape the response body takes."""
    for key in ("reply", "message", "response", "answer", "text", "content"):
        v = body.get(key)
        if isinstance(v, str) and v.strip():
            return v
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        return choices[0].get("message", {}).get("content", "") or ""
    return ""


def is_auth_error(status: int, body: dict) -> bool:
    raw = body.get("_raw", "") or str(body)
    return status == 403 or "allowlist" in raw.lower() or "not allowed" in raw.lower()


# ─── DATA COLLECTION ─────────────────────────────────────────────────────────

@dataclass
class EvalRow:
    """One collected bot response, ready for evaluation."""
    case:        EvalCase
    answer:      str        # actual bot reply
    http_status: int
    skipped:     bool = False
    skip_reason: str  = ""

    # Convenience pass-throughs
    @property
    def case_id(self):  return self.case.id
    @property
    def question(self): return self.case.query
    @property
    def expected(self): return self.case.expected
    @property
    def history(self):  return self.case.history


def collect_answers(cases: list[EvalCase], dry_run: bool = False) -> list[EvalRow]:
    """Call the Spacey chatbot for every eval case and store the replies."""
    rows: list[EvalRow] = []

    print(bold(f"\n{'─'*60}"))
    print(bold("  COLLECTING BOT RESPONSES"))
    print(bold(f"{'─'*60}"))

    for case in cases:
        if dry_run:
            print(f"  {dim('[dry-run]')} {cyan(case.id)}  {case.query[:60]}")
            rows.append(EvalRow(case, "[dry-run]", 0, skipped=True, skip_reason="dry-run"))
            continue

        tags_str = ", ".join(sorted(case.tags)) if case.tags else "—"
        print(f"  {cyan(case.id)}  {case.query[:45]:<45}  [{dim(tags_str)}]", end="  ", flush=True)
        time.sleep(PAUSE)
        status, body = post(case.query, case.history)

        if is_auth_error(status, body):
            raw = body.get("_raw", str(body))[:60]
            print(yellow("⊘ skipped (auth)"))
            rows.append(EvalRow(case, "", status, skipped=True, skip_reason=f"auth: {raw}"))
            continue

        reply = extract_reply(body)
        if not reply:
            print(yellow(f"⚠  HTTP {status} — no reply"))
            rows.append(EvalRow(case, "", status, skipped=True, skip_reason=f"HTTP {status}, no reply"))
            continue

        print(green(f"✔  HTTP {status} | {len(reply)} chars"))
        rows.append(EvalRow(case, reply, status))

    return rows


# ─── DEEPEVAL EVALUATION ─────────────────────────────────────────────────────

@dataclass
class MetricResult:
    """Score + reasoning for one metric on one test case."""
    name:   str
    score:  float
    reason: str
    passed: bool


@dataclass
class CaseResult:
    """All metric scores for a single eval case."""
    case_id:  str
    question: str
    answer:   str
    expected: str
    tags:     set
    metrics:  list[MetricResult] = field(default_factory=list)

    @property
    def avg_score(self) -> float:
        return sum(m.score for m in self.metrics) / len(self.metrics) if self.metrics else 0.0


def _build_metrics(row: EvalRow, imports: dict) -> list:
    """
    Return the metric instances appropriate for this case.

    Core (all cases):
      AnswerRelevancyMetric, GEval(Correctness), GEval(Conciseness)

    Selective:
      "search"       → TaskCompletionMetric
      "handoff"      → TaskCompletionMetric
      "off-topic"    → TopicAdherenceMetric
      "empty"        → GEval(Empathy)
      "amenity"      → GEval(AmenityAccuracy)
      "chip-removal" → GEval(ChipRemoval)
      "browse-mode"  → GEval(ModeLanguage)
      "multi-turn"   → KnowledgeRetentionMetric (handled separately via ConversationalTestCase)
    """
    AnswerRelevancyMetric  = imports["AnswerRelevancyMetric"]
    GEval                  = imports["GEval"]
    SingleTurnParams       = imports["SingleTurnParams"]
    TaskCompletionMetric   = imports["TaskCompletionMetric"]
    TopicAdherenceMetric   = imports["TopicAdherenceMetric"]

    # ── Core metrics ──────────────────────────────────────────────────────
    metrics = [
        AnswerRelevancyMetric(threshold=PASS_THRESHOLD, model=EVAL_MODEL, verbose_mode=False),

        GEval(
            name="Correctness",
            criteria=(
                "Evaluate whether the chatbot's actual_output correctly fulfils the "
                "expected behaviour described in expected_output, given the user's input. "
                "Score high if the response matches the expectation; low if it does not."
            ),
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.EXPECTED_OUTPUT,
            ],
            threshold=PASS_THRESHOLD,
            model=EVAL_MODEL,
            verbose_mode=False,
        ),

        # Spacey's text reply must be short (1–2 sentences).
        # It should NOT list spaces in plain text — cards carry that.
        GEval(
            name="Conciseness",
            criteria=(
                "Evaluate whether the chatbot's actual_output is appropriately concise "
                "(1–2 short sentences). The bot should NOT reproduce a bullet list of "
                "spaces in plain text, and should NOT give a wall-of-text reply. "
                "Score high for brief, focused replies; low for verbose or listy ones."
            ),
            evaluation_params=[
                SingleTurnParams.ACTUAL_OUTPUT,
            ],
            threshold=PASS_THRESHOLD,
            model=EVAL_MODEL,
            verbose_mode=False,
        ),
    ]

    # ── Selective metrics ─────────────────────────────────────────────────
    tags = row.case.tags

    if tags.intersection({"search", "handoff"}):
        task_desc = (
            "The chatbot is a workspace-booking assistant. Given the user's request, "
            "it should identify the space type, apply any stated filters (city, budget, "
            "date, capacity, amenities), and return relevant workspace results or take the "
            "appropriate action (e.g. handoff to human agent)."
        )
        metrics.append(
            TaskCompletionMetric(
                threshold=PASS_THRESHOLD,
                task=task_desc,
                model=EVAL_MODEL,
                verbose_mode=False,
            )
        )

    if "off-topic" in tags:
        metrics.append(
            TopicAdherenceMetric(
                relevant_topics=[
                    "workspace booking",
                    "finding a space in Sri Lanka",
                    "meeting rooms",
                    "coworking",
                    "office spaces",
                    "studio rental",
                    "MillionSpaces",
                ],
                threshold=PASS_THRESHOLD,
                model=EVAL_MODEL,
                verbose_mode=False,
            )
        )

    if "empty" in tags:
        metrics.append(
            GEval(
                name="Empathy",
                criteria=(
                    "When no spaces match the user's filters, evaluate whether the chatbot "
                    "responds with empathy and offers constructive alternatives "
                    "(e.g. broaden location, remove budget cap, try Colombo). "
                    "Score high for warm, helpful empty-state handling; "
                    "low for a cold 'no results' with no suggestions."
                ),
                evaluation_params=[
                    SingleTurnParams.INPUT,
                    SingleTurnParams.ACTUAL_OUTPUT,
                ],
                threshold=PASS_THRESHOLD,
                model=EVAL_MODEL,
                verbose_mode=False,
            )
        )

    if "amenity" in tags:
        # Extract amenity names mentioned in the query to embed in the criteria
        query_snippet = row.case.query[:120]
        metrics.append(
            GEval(
                name="AmenityAccuracy",
                criteria=(
                    "The user requested results filtered by specific amenities. "
                    f"User query: '{query_snippet}'. "
                    "Evaluate whether the chatbot response indicates that the amenity filter(s) "
                    "from the user's query are being applied. "
                    "The response should confirm filtering by the requested amenity/amenities "
                    "(by mentioning them or clearly acknowledging the filter), and should NOT "
                    "return generic results that ignore the amenity constraint. "
                    "For natural-language amenity requests (e.g. 'charge my laptop' = Charging points), "
                    "check that the bot correctly maps the intent to the right amenity. "
                    "Score high if amenity filtering is confirmed; low if amenities are ignored "
                    "or incorrectly mapped."
                ),
                evaluation_params=[
                    SingleTurnParams.INPUT,
                    SingleTurnParams.ACTUAL_OUTPUT,
                    SingleTurnParams.EXPECTED_OUTPUT,
                ],
                threshold=PASS_THRESHOLD,
                model=EVAL_MODEL,
                verbose_mode=False,
            )
        )

    if "chip-removal" in tags:
        metrics.append(
            GEval(
                name="ChipRemoval",
                criteria=(
                    "This message is a system-generated chip-removal request "
                    "(triggered when the user clicked ✕ on a filter chip). "
                    "Evaluate whether the chatbot correctly re-runs the search with "
                    "the specified filter removed while retaining all other active filters "
                    "from prior conversation context. "
                    "The response must NOT ask for information already provided in history. "
                    "Score high if: (a) the removed filter is no longer applied, "
                    "(b) all other prior filters are retained, "
                    "(c) new results are presented without asking redundant questions. "
                    "Score low if the bot ignores the removal, resets all filters, "
                    "or asks for already-known information."
                ),
                evaluation_params=[
                    SingleTurnParams.INPUT,
                    SingleTurnParams.ACTUAL_OUTPUT,
                    SingleTurnParams.EXPECTED_OUTPUT,
                ],
                threshold=PASS_THRESHOLD,
                model=EVAL_MODEL,
                verbose_mode=False,
            )
        )

    if "browse-mode" in tags:
        metrics.append(
            GEval(
                name="ModeLanguage",
                criteria=(
                    "Spacey operates in two modes: "
                    "(1) BROWSE MODE when no date is given — correct labels are "
                    "'Spaces You May Like' and 'View Details'; the bot must NOT say "
                    "'Available Spaces', 'Book Now', 'available slots', or 'available' "
                    "in an availability sense. "
                    "(2) AVAILABILITY MODE when the user has provided a date — correct "
                    "labels are 'Available Spaces' and 'Book Now'. "
                    "Evaluate whether the chatbot's actual_output uses the correct "
                    "mode language given the presence or absence of a date in the input. "
                    "Score high if mode language is correct or neutral; "
                    "score low if the wrong mode language is used "
                    "(e.g. saying 'available' when no date was given, "
                    "or using browse language after a date was provided)."
                ),
                evaluation_params=[
                    SingleTurnParams.INPUT,
                    SingleTurnParams.ACTUAL_OUTPUT,
                ],
                threshold=PASS_THRESHOLD,
                model=EVAL_MODEL,
                verbose_mode=False,
            )
        )

    return metrics



def _safe_measure(metric, test_case) -> MetricResult:
    """Measure one metric and catch exceptions gracefully."""
    name = getattr(metric, "name", metric.__class__.__name__)
    try:
        metric.measure(test_case)
        return MetricResult(
            name=name,
            score=round(metric.score, 3),
            reason=metric.reason or "",
            passed=metric.is_successful(),
        )
    except Exception as exc:
        return MetricResult(name=name, score=0.0, reason=f"error: {exc}", passed=False)


def run_deepeval(rows: list[EvalRow], fail_fast: bool = False) -> Optional[list[CaseResult]]:
    """
    Run deepeval metrics on every valid row.

    Single-turn cases  → LLMTestCase
    Multi-turn cases   → also builds a ConversationalTestCase for KnowledgeRetentionMetric
    fail_fast          → stop immediately after the first metric failure
    """
    valid = [r for r in rows if not r.skipped and r.answer]
    if not valid:
        print(yellow("\n  No valid rows to evaluate."))
        return None

    try:
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            GEval,
            KnowledgeRetentionMetric,
            TaskCompletionMetric,
            TopicAdherenceMetric,
        )
        from deepeval.test_case import (
            ConversationalTestCase,
            LLMTestCase,
            SingleTurnParams,
            Turn,
        )
    except ImportError as e:
        print(f"\n  ✘ Import error: {e}")
        print(dim("  Run:  pip install deepeval"))
        return None

    imports = {
        "AnswerRelevancyMetric": AnswerRelevancyMetric,
        "GEval":                 GEval,
        "SingleTurnParams":      SingleTurnParams,
        "TaskCompletionMetric":  TaskCompletionMetric,
        "TopicAdherenceMetric":  TopicAdherenceMetric,
    }

    print(bold(f"\n{'─'*60}"))
    print(bold("  RUNNING DEEPEVAL EVALUATION"))
    print(bold(f"{'─'*60}"))
    print(dim(f"  Cases   : {len(valid)}"))
    print(dim(f"  Metrics : AnswerRelevancy · Correctness · Conciseness"))
    print(dim(f"            + TaskCompletion  (search / handoff)"))
    print(dim(f"            + TopicAdherence  (off-topic)"))
    print(dim(f"            + KnowledgeRetention (multi-turn)"))
    print(dim(f"            + Empathy        (empty-result)"))
    print(dim(f"            + AmenityAccuracy (amenity)"))
    print(dim(f"            + ChipRemoval    (chip-removal)"))
    print(dim(f"            + ModeLanguage   (browse-mode)\n"))

    results: list[CaseResult] = []

    for row in valid:
        print(f"  {cyan(row.case_id)}  {row.question[:48]}", end="  ", flush=True)

        # ── Build LLMTestCase ────────────────────────────────────────────
        context_input = row.question
        if row.history:
            summary = " | ".join(
                f"{m['role']}: {m['content'][:40]}" for m in row.history
            )
            context_input = f"[Prior conversation: {summary}]  User: {row.question}"

        test_case = LLMTestCase(
            input=context_input,
            actual_output=row.answer,
            expected_output=row.expected,
        )

        # ── Build ConversationalTestCase for KnowledgeRetention ──────────
        conv_test_case: Optional[object] = None
        if "multi-turn" in row.case.tags and row.history:
            turns = []
            for m in row.history:
                turns.append(Turn(role=m["role"], content=m["content"]))
            turns.append(Turn(role="user",      content=row.question))
            turns.append(Turn(role="assistant", content=row.answer))
            conv_test_case = ConversationalTestCase(turns=turns)

        # ── Run metrics ──────────────────────────────────────────────────
        case_result = CaseResult(
            case_id=row.case_id,
            question=row.question,
            answer=row.answer,
            expected=row.expected,
            tags=row.case.tags,
        )

        for metric in _build_metrics(row, imports):
            mr = _safe_measure(metric, test_case)
            case_result.metrics.append(mr)
            if fail_fast and not mr.passed:
                colour = yellow
                print(colour(f"avg={case_result.avg_score:.2f}  ✘ FAIL-FAST on [{mr.name}]"))
                results.append(case_result)
                return results

        # KnowledgeRetentionMetric needs a ConversationalTestCase
        if conv_test_case is not None:
            kr_metric = KnowledgeRetentionMetric(
                threshold=PASS_THRESHOLD, model=EVAL_MODEL, verbose_mode=False
            )
            kr_result = _safe_measure(kr_metric, conv_test_case)
            case_result.metrics.append(kr_result)
            if fail_fast and not kr_result.passed:
                colour = yellow
                print(colour(f"avg={case_result.avg_score:.2f}  ✘ FAIL-FAST on [KnowledgeRetention]"))
                results.append(case_result)
                return results

        colour = green if case_result.avg_score >= 0.5 else yellow
        print(colour(f"avg={case_result.avg_score:.2f}"))
        results.append(case_result)

    return results


# ─── REPORT ──────────────────────────────────────────────────────────────────

def print_report(rows: list[EvalRow], results: Optional[list[CaseResult]]) -> None:
    total   = len(rows)
    skipped = sum(1 for r in rows if r.skipped)
    scored  = total - skipped

    print(bold(f"\n{'═'*60}"))
    print(bold("  EVALUATION SUMMARY"))
    print(bold(f"{'═'*60}"))
    print(f"  Total cases  : {bold(str(total))}")
    print(f"  Scored       : {bold(green(str(scored)))}")
    print(f"  Skipped      : {bold(yellow(str(skipped)))}")

    if skipped:
        print(f"\n  {yellow('Skipped:')}")
        for r in rows:
            if r.skipped:
                print(f"    {dim(r.case_id + ':')}  {r.skip_reason}")

    if not results:
        print()
        return

    # ── Per-case table ────────────────────────────────────────────────────
    # Collect all unique metric names in order of first appearance
    seen: dict[str, None] = {}
    for cr in results:
        for m in cr.metrics:
            seen[m.name] = None
    all_metric_names = list(seen)

    print(bold(f"\n  {'─'*58}"))
    print(bold("  PER-CASE SCORES  (0 → 1, higher is better)"))
    print(bold(f"  {'─'*58}"))

    col_w = 12
    header = f"  {'ID':<6}  {'Query':<30}  {'Tags':<18}  " + "  ".join(
        f"{n[:col_w]:<{col_w}}" for n in all_metric_names
    )
    print(dim(header))
    print(dim("  " + "─" * (len(header) - 2)))

    for cr in results:
        tags_str = ",".join(sorted(cr.tags)) if cr.tags else "—"
        row_str  = f"  {cr.case_id:<6}  {cr.question[:30]:<30}  {tags_str[:18]:<18}"
        metric_map = {m.name: m for m in cr.metrics}
        for name in all_metric_names:
            m = metric_map.get(name)
            if m:
                colour = green if m.passed else yellow
                row_str += f"  {colour(f'{m.score:.3f}'):<{col_w}}"
            else:
                row_str += f"  {'—':<{col_w}}"
        print(row_str)

    # ── Metric averages with progress bars ────────────────────────────────
    print(bold(f"\n  {'─'*58}"))
    print(bold("  METRIC AVERAGES  (across cases where metric was applied)"))
    print(bold(f"  {'─'*58}"))

    for name in all_metric_names:
        scores = [m.score for cr in results for m in cr.metrics if m.name == name]
        if not scores:
            continue
        avg     = sum(scores) / len(scores)
        bar_len = 28
        filled  = round(bar_len * avg)
        bar     = green("█" * filled) + dim("░" * (bar_len - filled))
        colour  = green if avg >= 0.5 else yellow
        print(f"  {name:<26}  [{bar}]  {colour(f'{avg:.3f}')}  (n={len(scores)})")

    all_scores = [m.score for cr in results for m in cr.metrics]
    if all_scores:
        overall = sum(all_scores) / len(all_scores)
        colour  = green if overall >= 0.5 else yellow
        print(bold(f"\n  Overall average : {colour(f'{overall:.3f}')}"))

    # ── Failures spotlight ────────────────────────────────────────────────
    failures = [
        (cr, m)
        for cr in results
        for m in cr.metrics
        if not m.passed
    ]
    if failures:
        print(bold(f"\n  {'─'*58}"))
        print(bold(f"  FAILURES  ({len(failures)} metric(s) below threshold)"))
        print(bold(f"  {'─'*58}"))
        for cr, m in failures[:15]:          # cap at 15 to keep output readable
            print(f"  {yellow(cr.case_id)}  [{m.name}]  score={m.score:.3f}")
            if m.reason:
                short = m.reason[:120].replace("\n", " ")
                print(f"    {dim(short)}")

    print()


# ─── CSV OUTPUT ──────────────────────────────────────────────────────────────

def save_csv(rows: list[EvalRow], results: Optional[list[CaseResult]],
             path: str = "spacey_deepeval_results.csv") -> None:
    """Write per-case scores and LLM reasoning to a CSV file."""
    result_map = {cr.case_id: cr for cr in results} if results else {}

    seen: dict[str, None] = {}
    if results:
        for cr in results:
            for m in cr.metrics:
                seen[m.name] = None
    metric_names = list(seen)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["case_id", "tags", "question", "expected", "answer",
             "http_status", "skipped", "skip_reason"]
            + metric_names
            + [f"{n}_reason" for n in metric_names]
        )
        for row in rows:
            cr      = result_map.get(row.case_id)
            mmap    = {m.name: m for m in cr.metrics} if cr else {}
            scores  = [mmap[n].score  if n in mmap else "" for n in metric_names]
            reasons = [mmap[n].reason if n in mmap else "" for n in metric_names]
            tags_str = "|".join(sorted(row.case.tags))
            writer.writerow([
                row.case_id, tags_str, row.question, row.expected, row.answer,
                row.http_status, row.skipped, row.skip_reason,
                *scores, *reasons,
            ])

    print(dim(f"  Results saved → {path}"))


# ─── HTML REPORT ─────────────────────────────────────────────────────────────

def _load_chartjs_source() -> str:
    """
    Return the Chart.js UMD source to embed inline in the HTML report.

    Embedding (rather than linking a CDN) keeps the report a single
    self-contained file that renders correctly offline, in sandboxed
    environments, or behind restrictive network/proxy policies.

    Looks for vendor/chart.umd.min.js next to this script. If missing,
    falls back to a CDN <script src> tag (will require network access
    to render charts when the report is opened).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    vendored = os.path.join(here, "vendor", "chart.umd.min.js")
    if os.path.exists(vendored):
        with open(vendored, "r", encoding="utf-8") as f:
            return f.read()
    return (
        "</script>\n"
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js">'
    )


def save_html(rows: list[EvalRow], results: Optional[list[CaseResult]],
              path: str = "spacey_deepeval_report.html") -> None:
    """Generate a self-contained HTML report of evaluation results."""
    import html as _html

    def esc(s) -> str:
        return _html.escape(str(s))

    now       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total     = len(rows)
    skipped   = sum(1 for r in rows if r.skipped)
    scored    = total - skipped

    # Collect metric names
    seen: dict[str, None] = {}
    if results:
        for cr in results:
            for m in cr.metrics:
                seen[m.name] = None
    metric_names = list(seen)

    result_map = {cr.case_id: cr for cr in results} if results else {}

    # ── Overall stats ──────────────────────────────────────────────────────
    all_scores    = [m.score for cr in (results or []) for m in cr.metrics]
    overall_avg   = sum(all_scores) / len(all_scores) if all_scores else 0.0
    failure_count = sum(1 for cr in (results or []) for m in cr.metrics if not m.passed)

    # ── Per-metric averages ────────────────────────────────────────────────
    metric_avgs: dict[str, tuple[float, int]] = {}
    for name in metric_names:
        scores = [m.score for cr in (results or []) for m in cr.metrics if m.name == name]
        metric_avgs[name] = (sum(scores) / len(scores) if scores else 0.0, len(scores))

    # ── Skipped rows ──────────────────────────────────────────────────────
    skipped_rows = [r for r in rows if r.skipped]

    # ── Failures ──────────────────────────────────────────────────────────
    failures = [
        (cr, m)
        for cr in (results or [])
        for m in cr.metrics
        if not m.passed
    ]

    # ── Per-case average score (one point per case, for the case-avg chart) ─
    case_avgs: list[tuple[str, float]] = [(cr.case_id, cr.avg_score) for cr in (results or [])]
    case_avg_of_avgs = (
        sum(a for _, a in case_avgs) / len(case_avgs) if case_avgs else 0.0
    )

    # ── Score distribution histogram (10 buckets, 0.0–1.0) ─────────────────
    hist_buckets = [0] * 10
    for s in all_scores:
        idx = min(9, int(s * 10))
        hist_buckets[idx] += 1
    hist_labels = [f"{i/10:.1f}\u2013{(i+1)/10:.1f}" for i in range(10)]

    # ── Per-tag breakdown (avg score + pass rate per tag) ───────────────────
    tag_scores: dict[str, list[float]] = {}
    tag_pass: dict[str, list[bool]] = {}
    for cr in (results or []):
        for t in (cr.tags or {"untagged"}):
            tag_scores.setdefault(t, []).append(cr.avg_score)
            for m in cr.metrics:
                tag_pass.setdefault(t, []).append(m.passed)
    tag_labels = sorted(tag_scores.keys())
    tag_avg_vals = [round(sum(tag_scores[t]) / len(tag_scores[t]), 3) for t in tag_labels]
    tag_pass_rates = [
        round(100 * sum(tag_pass.get(t, [False])) / max(1, len(tag_pass.get(t, []))), 1)
        for t in tag_labels
    ]

    def score_class(score: float) -> str:
        if score >= 0.75: return "pass-high"
        if score >= 0.50: return "pass-low"
        return "fail"

    def avg_class(avg: float) -> str:
        return "pass" if avg >= 0.5 else "fail"

    # ── Build per-case rows ────────────────────────────────────────────────
    case_rows_html = ""
    for cr in (results or []):
        tags_str = ", ".join(sorted(cr.tags)) if cr.tags else "—"
        metric_cells = ""
        for name in metric_names:
            m = next((x for x in cr.metrics if x.name == name), None)
            if m:
                cls   = score_class(m.score)
                icon  = "✔" if m.passed else "✘"
                tip   = esc(m.reason[:200]) if m.reason else ""
                metric_cells += (
                    f'<td class="{cls}" title="{tip}">'
                    f'{icon} {m.score:.3f}</td>'
                )
            else:
                metric_cells += '<td class="na">—</td>'

        avg_cls = avg_class(cr.avg_score)
        case_rows_html += f"""
        <tr>
          <td class="mono">{esc(cr.case_id)}</td>
          <td>{esc(cr.question)}</td>
          <td><span class="tags">{esc(tags_str)}</span></td>
          {metric_cells}
          <td class="{avg_cls}"><strong>{cr.avg_score:.3f}</strong></td>
        </tr>"""

    # ── Metric header cells ────────────────────────────────────────────────
    metric_th = "".join(f"<th>{esc(n)}</th>" for n in metric_names)

    # ── Metric averages rows ───────────────────────────────────────────────
    metric_avg_rows = ""
    for name, (avg, n) in metric_avgs.items():
        bar_pct = round(avg * 100)
        cls     = avg_class(avg)
        metric_avg_rows += f"""
        <tr>
          <td>{esc(name)}</td>
          <td>
            <div class="bar-wrap">
              <div class="bar {cls}" style="width:{bar_pct}%"></div>
            </div>
          </td>
          <td class="{cls}"><strong>{avg:.3f}</strong></td>
          <td class="dim">n={n}</td>
        </tr>"""

    # ── Skipped rows ──────────────────────────────────────────────────────
    skipped_html = ""
    if skipped_rows:
        for r in skipped_rows:
            skipped_html += f"""
        <tr>
          <td class="mono">{esc(r.case_id)}</td>
          <td>{esc(r.question)}</td>
          <td>{esc(r.skip_reason)}</td>
        </tr>"""

    # ── Failures ──────────────────────────────────────────────────────────
    failures_html = ""
    for cr, m in failures[:20]:
        short_reason = (m.reason or "")[:200].replace("\n", " ")
        failures_html += f"""
        <tr>
          <td class="mono">{esc(cr.case_id)}</td>
          <td>{esc(m.name)}</td>
          <td class="fail">{m.score:.3f}</td>
          <td class="dim">{esc(short_reason)}</td>
        </tr>"""

    # ── Assemble HTML ──────────────────────────────────────────────────────
    overall_cls = avg_class(overall_avg)

    import json as _json
    chart_data = _json.dumps({
        "metricNames":   metric_names,
        "metricAvgs":    [round(metric_avgs[n][0], 3) for n in metric_names],
        "metricN":       [metric_avgs[n][1] for n in metric_names],
        "tagLabels":     tag_labels,
        "tagAvgs":       tag_avg_vals,
        "tagPassRates":  tag_pass_rates,
        "histLabels":    hist_labels,
        "histCounts":    hist_buckets,
        "passCount":     len(all_scores) - failure_count,
        "failCount":     failure_count,
        "overallAvg":    round(overall_avg, 3),
    })

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Spacey DeepEval Report — {now}</title>
<script>
{_load_chartjs_source()}
</script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    background: #f7f8fa;
    color: #1a1a2e;
    padding: 32px 24px;
  }}

  header {{
    margin-bottom: 28px;
  }}
  header h1 {{
    font-size: 22px;
    font-weight: 700;
    color: #0f172a;
  }}
  header p {{
    color: #64748b;
    margin-top: 4px;
    font-size: 13px;
  }}

  .summary-cards {{
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    margin-bottom: 28px;
  }}
  .card {{
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 22px;
    min-width: 140px;
  }}
  .card .label {{ font-size: 11px; text-transform: uppercase; color: #94a3b8; letter-spacing: .05em; }}
  .card .value {{ font-size: 26px; font-weight: 700; margin-top: 4px; }}
  .card .value.pass {{ color: #16a34a; }}
  .card .value.fail {{ color: #dc2626; }}
  .card .value.neutral {{ color: #0f172a; }}

  section {{
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    margin-bottom: 24px;
    overflow: hidden;
  }}
  section h2 {{
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: #475569;
    padding: 14px 20px;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  th, td {{
    text-align: left;
    padding: 9px 14px;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: top;
  }}
  th {{
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: #64748b;
    background: #f8fafc;
    white-space: nowrap;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f8fafc; }}

  .mono {{ font-family: monospace; font-size: 12px; color: #334155; }}
  .dim  {{ color: #94a3b8; font-size: 12px; }}
  .na   {{ color: #cbd5e1; text-align: center; }}
  .tags {{
    display: inline-block;
    font-size: 11px;
    background: #eff6ff;
    color: #3b82f6;
    border-radius: 4px;
    padding: 2px 7px;
  }}

  .pass-high {{ color: #16a34a; }}
  .pass-low  {{ color: #65a30d; }}
  .fail      {{ color: #dc2626; }}
  .pass      {{ color: #16a34a; }}
  .warn      {{ color: #d97706; }}

  .bar-wrap {{
    width: 180px;
    height: 10px;
    background: #f1f5f9;
    border-radius: 99px;
    overflow: hidden;
  }}
  .bar {{
    height: 100%;
    border-radius: 99px;
    transition: width .3s;
  }}
  .bar.pass {{ background: #22c55e; }}
  .bar.fail {{ background: #ef4444; }}

  .empty {{ padding: 20px; color: #94a3b8; font-style: italic; }}

  /* ── Charts ──────────────────────────────────────────────────────────── */
  .charts-grid {{
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 20px;
    padding: 20px;
  }}
  @media (max-width: 900px) {{
    .charts-grid {{ grid-template-columns: 1fr; }}
  }}
  .chart-card {{
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px;
  }}
  .chart-card h3 {{
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: #64748b;
    margin-bottom: 12px;
  }}
  .chart-card canvas {{ max-width: 100%; }}
  .ring-card {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
  }}
  .ring-wrap {{ position: relative; width: 200px; height: 200px; }}
  .ring-label {{
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }}
  .ring-label .big {{ font-size: 32px; font-weight: 800; color: #0f172a; }}
  .ring-label .small {{ font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: .05em; margin-top: 2px; }}
  .charts-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  @media (max-width: 900px) {{
    .charts-row {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<header>
  <h1>🤖 Spacey — DeepEval Chatbot Evaluation Report</h1>
  <p>Generated {now} &nbsp;·&nbsp; Endpoint: {esc(BASE_URL)}</p>
</header>

<!-- Summary cards -->
<div class="summary-cards">
  <div class="card">
    <div class="label">Total Cases</div>
    <div class="value neutral">{total}</div>
  </div>
  <div class="card">
    <div class="label">Scored</div>
    <div class="value pass">{scored}</div>
  </div>
  <div class="card">
    <div class="label">Skipped</div>
    <div class="value {'fail' if skipped else 'neutral'}">{skipped}</div>
  </div>
  <div class="card">
    <div class="label">Overall Avg</div>
    <div class="value {overall_cls}">{overall_avg:.3f}</div>
  </div>
  <div class="card">
    <div class="label">Failures</div>
    <div class="value {'fail' if failure_count else 'pass'}">{failure_count}</div>
  </div>
</div>

<!-- Visual charts -->
<section>
  <h2>Score Overview</h2>
  <div class="charts-grid">
    <div class="chart-card ring-card">
      <h3>Overall Avg Score</h3>
      <div class="ring-wrap">
        <canvas id="ringChart"></canvas>
        <div class="ring-label">
          <div class="big">{overall_avg:.2f}</div>
          <div class="small">{failure_count} below threshold</div>
        </div>
      </div>
    </div>
    <div class="chart-card">
      <h3>Average Score by Metric</h3>
      <canvas id="metricChart" height="90"></canvas>
    </div>
  </div>
  <div class="charts-grid" style="grid-template-columns: 1fr 1fr;">
    <div class="chart-card">
      <h3>Score Distribution (all metric scores)</h3>
      <canvas id="histChart" height="110"></canvas>
    </div>
    <div class="chart-card">
      <h3>Avg Score &amp; Pass Rate by Tag</h3>
      <canvas id="tagChart" height="110"></canvas>
    </div>
  </div>
</section>

<!-- Per-case scores -->
<section>
  <h2>Per-Case Scores</h2>
  {'<table><thead><tr><th>ID</th><th>Query</th><th>Tags</th>' + metric_th + '<th>Avg</th></tr></thead><tbody>' + case_rows_html + '</tbody></table>'
   if results else '<div class="empty">No evaluation results available.</div>'}
</section>

<!-- Metric averages -->
<section>
  <h2>Metric Averages</h2>
  {'<table><thead><tr><th>Metric</th><th>Score</th><th></th><th></th></tr></thead><tbody>' + metric_avg_rows + '</tbody></table>'
   if metric_avg_rows else '<div class="empty">No metrics data.</div>'}
</section>

<!-- Failures -->
<section>
  <h2>Failures ({len(failures)} metric(s) below threshold)</h2>
  {'<table><thead><tr><th>ID</th><th>Metric</th><th>Score</th><th>Reason</th></tr></thead><tbody>' + failures_html + '</tbody></table>'
   if failures_html else '<div class="empty">No failures — all metrics passed.</div>'}
</section>

<!-- Skipped -->
{'<section><h2>Skipped Cases</h2><table><thead><tr><th>ID</th><th>Query</th><th>Reason</th></tr></thead><tbody>' + skipped_html + '</tbody></table></section>'
 if skipped_rows else ''}

<script>
  const CHART_DATA = {chart_data};

  const PALETTE = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#84cc16','#f97316','#64748b'];

  Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  Chart.defaults.font.size = 11;
  Chart.defaults.color = '#64748b';

  // Overall score ring (donut)
  new Chart(document.getElementById('ringChart'), {{
    type: 'doughnut',
    data: {{
      labels: ['Passed', 'Failed'],
      datasets: [{{
        data: [CHART_DATA.passCount, CHART_DATA.failCount],
        backgroundColor: ['#22c55e', '#ef4444'],
        borderWidth: 0,
      }}]
    }},
    options: {{
      cutout: '75%',
      plugins: {{ legend: {{ display: false }}, tooltip: {{ enabled: true }} }},
    }}
  }});

  // Average score per metric (horizontal bar)
  new Chart(document.getElementById('metricChart'), {{
    type: 'bar',
    data: {{
      labels: CHART_DATA.metricNames,
      datasets: [{{
        label: 'Avg Score',
        data: CHART_DATA.metricAvgs,
        backgroundColor: CHART_DATA.metricAvgs.map(v => v >= 0.75 ? '#22c55e' : v >= 0.5 ? '#65a30d' : '#ef4444'),
        borderRadius: 4,
      }}]
    }},
    options: {{
      indexAxis: 'y',
      scales: {{ x: {{ min: 0, max: 1, grid: {{ color: '#f1f5f9' }} }}, y: {{ grid: {{ display: false }} }} }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: (ctx) => `avg ${{ctx.parsed.x.toFixed(3)}}  (n=${{CHART_DATA.metricN[ctx.dataIndex]}})`
          }}
        }}
      }}
    }}
  }});

  // Score distribution histogram
  new Chart(document.getElementById('histChart'), {{
    type: 'bar',
    data: {{
      labels: CHART_DATA.histLabels,
      datasets: [{{
        label: 'Count',
        data: CHART_DATA.histCounts,
        backgroundColor: CHART_DATA.histLabels.map((_, i) => i >= 7 ? '#22c55e' : i >= 5 ? '#65a30d' : '#ef4444'),
        borderRadius: 4,
      }}]
    }},
    options: {{
      scales: {{ y: {{ beginAtZero: true, ticks: {{ precision: 0 }}, grid: {{ color: '#f1f5f9' }} }}, x: {{ grid: {{ display: false }} }} }},
      plugins: {{ legend: {{ display: false }} }}
    }}
  }});

  // Avg score + pass rate by tag (combo)
  new Chart(document.getElementById('tagChart'), {{
    type: 'bar',
    data: {{
      labels: CHART_DATA.tagLabels,
      datasets: [
        {{
          label: 'Avg Score',
          data: CHART_DATA.tagAvgs,
          backgroundColor: '#3b82f6',
          borderRadius: 4,
          yAxisID: 'y',
        }},
        {{
          label: 'Pass Rate %',
          data: CHART_DATA.tagPassRates,
          type: 'line',
          borderColor: '#f59e0b',
          backgroundColor: '#f59e0b',
          yAxisID: 'y1',
          tension: 0.3,
        }}
      ]
    }},
    options: {{
      scales: {{
        y:  {{ min: 0, max: 1,   position: 'left',  grid: {{ color: '#f1f5f9' }}, title: {{ display: true, text: 'Avg Score' }} }},
        y1: {{ min: 0, max: 100, position: 'right', grid: {{ display: false }},  title: {{ display: true, text: 'Pass Rate %' }} }},
        x:  {{ grid: {{ display: false }} }}
      }},
      plugins: {{ legend: {{ display: true, position: 'bottom' }} }}
    }}
  }});
</script>

</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)

    print(dim(f"  HTML report saved → {path}"))


# ─── JSON OUTPUT ─────────────────────────────────────────────────────────────

def save_json(rows: list[EvalRow], results: Optional[list[CaseResult]],
              path: str = "spacey_deepeval_results.json") -> None:
    """Write full evaluation results to a JSON file for downstream processing."""
    import json

    result_map = {cr.case_id: cr for cr in results} if results else {}

    output = {
        "generated_at": datetime.datetime.now().isoformat(),
        "endpoint": BASE_URL,
        "total_cases": len(rows),
        "scored": sum(1 for r in rows if not r.skipped),
        "skipped": sum(1 for r in rows if r.skipped),
        "cases": [],
    }

    for row in rows:
        cr = result_map.get(row.case_id)
        case_entry = {
            "id":          row.case_id,
            "query":       row.question,
            "tags":        sorted(row.case.tags),
            "expected":    row.expected,
            "answer":      row.answer,
            "http_status": row.http_status,
            "skipped":     row.skipped,
            "skip_reason": row.skip_reason,
            "metrics":     [],
            "avg_score":   round(cr.avg_score, 3) if cr else None,
        }
        if cr:
            for m in cr.metrics:
                case_entry["metrics"].append({
                    "name":   m.name,
                    "score":  m.score,
                    "passed": m.passed,
                    "reason": m.reason,
                })
        output["cases"].append(case_entry)

    # Overall averages per metric
    if results:
        seen: dict[str, list] = {}
        for cr in results:
            for m in cr.metrics:
                seen.setdefault(m.name, []).append(m.score)
        output["metric_averages"] = {
            name: round(sum(scores) / len(scores), 3)
            for name, scores in seen.items()
        }
        all_scores = [s for scores in seen.values() for s in scores]
        output["overall_avg"] = round(sum(all_scores) / len(all_scores), 3) if all_scores else None

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(dim(f"  JSON results saved → {path}"))


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Spacey — DeepEval chatbot quality evaluation (v4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Requires:  pip install deepeval requests python-dotenv\n"
            "Auth:      export OPENAI_API_KEY=sk-...\n"
            "           Add Cookie/Authorization to AUTH_HEADERS if you get 403 errors.\n"
            "\nExamples:\n"
            "  python spacey_deepeval_v4.py\n"
            "  python spacey_deepeval_v4.py --dry-run\n"
            "  python spacey_deepeval_v4.py --output\n"
            "  python spacey_deepeval_v4.py --html\n"
            "  python spacey_deepeval_v4.py --json\n"
            "  python spacey_deepeval_v4.py --fail-fast\n"
            "  python spacey_deepeval_v4.py --tags search amenity chip-removal\n"
        ),
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print dataset without calling the API or deepeval")
    parser.add_argument("--output", action="store_true",
                        help="Save results to spacey_deepeval_results.csv")
    parser.add_argument("--html", action="store_true",
                        help="Save results to spacey_deepeval_report.html")
    parser.add_argument("--json", action="store_true", dest="save_json_flag",
                        help="Save results to spacey_deepeval_results.json")
    parser.add_argument("--fail-fast", action="store_true",
                        help="Stop evaluation on the first metric failure")
    parser.add_argument("--tags", nargs="+", metavar="TAG",
                        help="Run only cases with at least one of the specified tags "
                             "(e.g. --tags search amenity chip-removal)")
    args = parser.parse_args()

    # Filter cases by tag if requested
    cases_to_run = EVAL_CASES
    if args.tags:
        filter_tags = set(args.tags)
        cases_to_run = [c for c in EVAL_CASES if c.tags.intersection(filter_tags)]
        if not cases_to_run:
            print(yellow(f"\n  No cases match tags: {filter_tags}"))
            raise SystemExit(1)

    all_tags = sorted({t for c in cases_to_run for t in c.tags})

    print(bold(f"\n{'═'*60}"))
    print(bold("  Spacey — DeepEval Chatbot Evaluation  (v4)"))
    print(bold(f"{'═'*60}"))
    print(dim(f"  Endpoint  : {BASE_URL}"))
    print(dim(f"  Cases     : {len(cases_to_run)}  ({', '.join(all_tags)})"))
    print(dim(f"  Fail-fast : {'on' if args.fail_fast else 'off'}"))
    print(dim(f"  Auth      : {'Custom headers set' if AUTH_HEADERS else 'None (add to AUTH_HEADERS if you get 403s)'}"))
    print(dim(f"  OpenAI key: {'✔ found' if os.getenv('OPENAI_API_KEY') else '✘ not set — export OPENAI_API_KEY=sk-...'}"))

    if not args.dry_run and not os.getenv("OPENAI_API_KEY"):
        print(yellow("\n  ⚠  OPENAI_API_KEY is not set. DeepEval scoring will fail."))
        print(dim("     Set it with:  export OPENAI_API_KEY=sk-..."))
        print(dim("     Or use --dry-run to collect responses only.\n"))

    # Step 1 — Collect chatbot responses
    rows = collect_answers(cases_to_run, dry_run=args.dry_run)

    # Step 2 — Run deepeval metrics (skipped in dry-run mode)
    results = None
    if not args.dry_run:
        results = run_deepeval(rows, fail_fast=args.fail_fast)

    # Step 3 — Print report
    print_report(rows, results)

    # Step 4 — Optionally save to CSV
    if args.output:
        save_csv(rows, results)

    # Step 5 — Optionally save HTML report
    if args.html:
        save_html(rows, results)

    # Step 6 — Optionally save JSON
    if args.save_json_flag:
        save_json(rows, results)

