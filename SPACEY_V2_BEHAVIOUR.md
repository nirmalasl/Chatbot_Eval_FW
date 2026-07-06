# Spacey V2 — Behaviour Reference

> **Purpose:** Describes how Spacey (Agent V2) behaves in the product — for anyone who needs to understand or explore it (product, support, engineering, or validation). This is **not** a prescribed test plan; teams can use their own methods and coverage.  
> **Product:** **Spacey** — the floating chat assistant on MillionSpaces (Sri Lanka) that helps users find and book workspaces through natural conversation.  
> **Flag:** `REACT_APP_USE_AGENT_V2=true` in `ms-web`.

**Related:** [MS_AGENT_ARCHITECTURE.md](./MS_AGENT_ARCHITECTURE.md) · [Agent behaviour spec (engineering)](../ms-web/src/components/Agent/AGENT_BEHAVIOUR.md)

---

## 1. What is Spacey? (30-second overview)

Spacey is **not** a fixed step-by-step form. It is a **chat assistant** that:

1. Understands free-text messages (type, city, budget, date, capacity, etc.).
2. Calls a **backend agent** that searches **live** MillionSpaces inventory.
3. Shows **space cards** under Spacey’s short reply (Spacey does **not** list every space in text).
4. Lets users **refine** searches (“under 5000”, “in Kandy”, “this Friday”) or remove filters via **small chips** with an **✕** button.
5. Switches to **availability mode** only after the user gives a **date** — then cards show **available slots** (when the API returns them) and **Book Now** instead of **View Details**.

Users do **not** need to log in to use Spacey. Login only changes the **greeting** (name + booking count).

---

## 2. Where to find Spacey

| Item | Detail |
|------|--------|
| **Launcher** | Floating button (Spacey avatar) bottom-right on most site pages |
| **Speech bubble** | Optional teaser: *“Hi I'm Spacey, How can I help you today?”* — can be dismissed with **×** on the bubble (separate from the chat popup) |
| **Chat window** | Opens when the launcher is clicked |
| **Hidden on** | Active booking flow: URL path contains `/space/bookings` **and** query has `eventTypeId` |
| **Not shown until** | Workspace/activity data is loaded in the app (Redux) |

**Header controls (inside chat):**

| Control | Label in UI | Purpose |
|---------|-------------|---------|
| Reset chat | “Reset chat” (circular arrow) | **Clears** conversation and storage; fresh greeting |
| Close | X | **Closes** popup only — conversation is **kept** (see §7) |

---

## 3. Supported space types (only these 9)

If the user asks for retired types (dedicated desk, booth-only, etc.), Spacey should steer them to the list below.

| Category | Names users might say |
|----------|------------------------|
| **Work** | Individual Workspace (coworking, hot desk), Private Office, Virtual Office |
| **Meet** | Meeting Space (meeting room, boardroom), Interview Room, Team Building, Training |
| **Shoot** | Photo Shoot, Video Shoot |

Default market: **Sri Lanka (`LK`)**. Search can be **country-wide** or narrowed to a **city**.

---

## 4. Core behaviour

### 4.1 Progressive search (no interrogation)

- **Minimum to show cards:** user gives a **space type** (e.g. “photo shoot”, “meeting room”).
- **Location optional:** first search can be **all Sri Lanka**; city can be added later.
- **Date, budget, people count optional** until the user adds them.
- Spacey should show cards **within ~2 turns**, not ask for city before the first list.

### 4.2 Browse mode vs availability mode

| | **Browse mode** (no date from user) | **Availability mode** (user gave a date) |
|---|-------------------------------------|------------------------------------------|
| **Section title above cards** | **Spaces You May Like** | **Available Spaces** |
| **Card button** | **View Details →** | **Book Now →** |
| **Booking link** | Space booking page **without** pre-filled dates | Booking page **with** `urlStartDate` / `urlEndDate` |
| **Availability block on card** | Usually **hidden** | **Shown** when API returns slots or seats (see §5) |
| **Wording** | Spacey should **not** say spaces are “available” | May say “available” / slots |

**When the user adds a date:** the header becomes **Available Spaces**, the card button becomes **Book Now**, and the slot/seat section appears when the backend returns `availability`.

### 4.3 Filter chips (the “little cards” above results)

After a search (including **zero results**), a row of **chips** may appear under Spacey’s message. Each chip is one active filter:

| Chip | Example label | ✕ removes |
|------|---------------|-----------|
| Type | `photo shoot` | Space type filter |
| Location | `📍 Colombo` | City/area — search goes **country-wide** again |
| Date | `📅 21-05-2026` | Date — back to **browse mode** |
| Capacity | `👥 8+ people` | Minimum people count |
| Budget | `💰 ≤ LKR 10,000` | Max price cap |

**What happens when the user clicks ✕ on a chip**

1. The UI does **not** edit filters locally.
2. It sends a **synthetic user message** to the agent (as if the user typed it), for example:
   - Remove budget: `search without a budget limit`
   - Remove date: `show photo shoot in Colombo without a specific date`
   - Remove location: `show photo shoot across Sri Lanka`
   - Remove type: `show all space types in Colombo` (keeps location/budget if present)
3. That text appears as a **user** bubble in the thread, then **Thinking...**
4. The agent **re-runs search** with updated filters; a **new** reply + chips + cards (or empty/error panel) follow.
5. **Other chips’ filters stay** unless the new search no longer applies them.

**Important:** Removing the date chip must **not** silently keep “availability” labelling — the UI returns to browse mode.

### 4.4 Space result cards (the big cards)

Each card typically shows:

- Image (or building placeholder if image fails)
- Space name, host (“by …”)
- Address / city (optional distance in km)
- Price (e.g. `LKR 1,500 / hour`)
- Capacity (“Up to N people”)
- Up to **4 amenity tags** (+N more if many)
- **Availability section** (availability mode only): time slots (up to 3 + “more”) or seat count
- **View Details →** or **Book Now →** — opens booking in a **new tab**

Spacey’s text reply should stay **short** (1–2 sentences). A bullet list of all spaces in the chat bubble is **not** expected.

### 4.5 Pagination — “Show 10 more”

- First search shows up to **10** cards.
- If more matches exist, UI shows **Showing X of Y spaces** and **Show 10 more**.
- **Show 10 more** calls the backend **without** a new LLM turn (faster).
- Hard cap: **30** cards per search; beyond that, copy may ask to refine filters.

### 4.6 Follow-up questions (soft, not every turn)

| When | Expected behaviour |
|------|-------------------|
| **After first card list** | Spacey may **once** softly ask about budget or date (wording varies) |
| **After several refinements without a date** | Spacey may **once** nudge for a date to check real availability |
| **Most other turns** | **No** extra question — only intro + cards |

Exact wording will vary (LLM); **intent** matters more than exact strings.

### 4.7 Empty results

- Short empathetic message from Spacey.
- Panel with icon and **quick actions**, e.g.:
  - **Try Colombo** (if location was not Colombo)
  - **Search without date** (if date filter was set)
  - **Remove budget cap** (if budget was set)
- Chips remain visible so filters can be removed via ✕.

### 4.8 Search / connection errors

- **Try again** re-sends the same user message.
- **Talk to a human →** triggers human agent flow.
- Chips may still show for the failed search context.

### 4.9 Human agent & contact form

Triggers (any can work in practice):

- User types **agent**, **human**, “connect me to an agent”, etc.
- Error UI **Talk to a human →**

**Expected:**

- Contact form appears in the chat (name, email, phone, message).
- Phone link: **0117 811 811**
- Submit success / failure messages.

### 4.10 Offline

With network disabled, sending a message shows an offline bot message (no API call).

### 4.11 Booking from chat

- **Primary path:** user clicks **Book Now** / **View Details** on a card.
- **Secondary path:** user says e.g. “book the second one” — the agent may open a booking URL via a tool; this is less deterministic than the card button.

### 4.12 Commands & edge behaviour

| Scenario | Expected |
|----------|----------|
| Only location, no type | Ask **once** for space type (with examples) |
| Neither type nor location | Ask **once** for type only |
| Off-topic (weather, jokes) | Polite redirect to bookings |
| “What types do you have?” | Lists **9** types (Work / Meet / Shoot) |
| “How much does coworking cost?” | Hedge + often shows coworking cards country-wide |
| Change type mid-chat (“actually meeting room”) | New type; location/budget/date may **carry over** if still relevant |
| “anywhere” / remove location chip | Country-wide search, **not** default Colombo |
| Unsupported type (e.g. “dedicated desk”) | Explain 9 types; may suggest closest match |
| User on booking page (hidden rule) | Launcher/chat not shown |

---

## 5. Availability section on cards (detail)

Only in **availability mode** (user provided a date in the conversation):

1. **Time-slot spaces** (meetings, shoots, etc.):  
   - Label: **✓ Available slots**  
   - Up to **3** slot rows (`startTime – endTime`)  
   - If more: **+N more slots**

2. **Seat-based work spaces:**  
   - e.g. **✓ 5 seats available**

3. **Fallback:**  
   - **✓ Available** if API sent availability object but no slots/seats list

If no availability block appears but mode is availability, that may reflect **search API data** rather than the chat UI alone.

---

## 6. Example conversation flows

Illustrative multi-turn chats. Wording and timing vary; the tables describe **expected product behaviour**.

### Flow A — Country-wide → city → budget → date (full refinement)

| Step | User types | Expected behaviour |
|------|------------|-------------------|
| 1 | `I need a photo shoot space` | Cards appear; title **Spaces You May Like**; chip `photo shoot`; no location chip; soft follow-up about budget/date **may** appear |
| 2 | `Colombo` | New message + cards; chip `📍 Colombo`; results narrowed to Colombo area |
| 3 | `under 15000` | Cards refresh; chip `💰 ≤ LKR 15,000`; prices at or under cap |
| 4 | `for 6 people` | If supported for type, chip `👥 6+ people`; cards respect capacity |
| 5 | `on 21-05-2026` | Title **Available Spaces**; **Book Now**; date chip `📅 21-05-2026`; slot/seat block on cards if API provides it |
| 6 | Click ✕ on **budget** chip | Synthetic user message; budget chip gone; search without price cap; still Colombo + date |
| 7 | Click ✕ on **date** chip | Back to **Spaces You May Like** / **View Details**; browse mode |

---

### Flow B — Meeting room with follow-ups and pagination

| Step | User types | Expected behaviour |
|------|------------|-------------------|
| 1 | `meeting room in Kandy` | ~10 cards; chips: meeting space + Kandy |
| 2 | *(no message)* | Optional soft question about budget/date (not required) |
| 3 | `under 8000` | Filtered cards; budget chip added |
| 4 | `try again` | Same criteria re-searched (if previous turn had error) |
| 5 | If **Show 10 more** visible | Click → up to 10 more cards append (same message block); total ≤ 30 |
| 6 | `next Saturday` | Availability mode if date parsed; slots if returned |

---

### Flow C — Coworking Q&A then narrow

| Step | User types | Expected behaviour |
|------|------------|-------------------|
| 1 | `what kinds of spaces do you have?` | Lists 9 types; cards not required |
| 2 | `how much does coworking cost?` | Short hedge; cards for individual workspace / coworking; country-wide unless city named |
| 3 | `in Galle` | Location chip Galle; cards for Galle |
| 4 | `actually private office` | Type changes; Galle may remain |
| 5 | If zero results | Empty panel + **Try Colombo** if location ≠ Colombo |

---

### Flow D — Human handoff

| Step | User types | Expected behaviour |
|------|------------|-------------------|
| 1 | `studio for video shoot Colombo` | Cards + chips |
| 2 | `nothing works` / `agent` | Contact form; phone visible |
| 3 | Fill and submit form | Success thank-you OR error message |
| 4 | Close form area | Chat can continue |

---

### Flow E — Chip removal without typing

| Step | Action | Expected behaviour |
|------|--------|-------------------|
| 1 | `training room Colombo under 5000 on 15-06-2026` | All relevant chips present |
| 2 | Click ✕ on **location** only | Message like `show training across Sri Lanka under LKR 5,000 on 15-06-2026`; location chip gone; broader results |
| 3 | Click ✕ on **space type** | Message `show all space types in …`; type chip gone; new search |
| 4 | Thread | Each ✕ produces a **user** bubble before the bot reply |

---

### Flow F — Booking paths

| Step | Action | Expected behaviour |
|------|--------|-------------------|
| 1 | Search with **no date** | **View Details →** opens new tab; URL has space + event type; **no** date query params |
| 2 | Same thread, add date | **Book Now →**; URL includes date parameters |
| 3 | Compare two spaces | Different `spaceId` in URLs |

---

## 7. Persistence & storage

Spacey stores chat in the browser **`sessionStorage`** (key: `spacey_v2_session`), **per browser tab**.  
The server does **not** store chat history between requests; each API call sends `history` from the client.

### 7.1 What is saved

| Data | Saved? |
|------|--------|
| Visible messages (bubbles, cards, errors) | Yes |
| LLM history (for context on next message) | Yes |
| In-flight “Thinking...” bubble | No (stripped before save) |

### 7.2 Scenario matrix

| Scenario | Chat restored when reopening Spacey? | Notes |
|----------|--------------------------------------|-------|
| Close popup with **X** (minimize) | **Yes** | Same tab; state also kept in memory while app stays open |
| Click launcher again after close | **Yes** | Same conversation |
| **Refresh page** (F5) in **same tab** | **Yes** | Loaded from `sessionStorage` |
| **Close browser tab** | **No** | `sessionStorage` cleared for that tab |
| Open site in **new tab** | **No** | Fresh greeting |
| Click **Reset chat** | **No** | Storage cleared + new greeting |
| **Logout** (was logged in) | **No** | Session cleared intentionally |
| **Login** while guest chat existed | Guest session may persist until logout (product-dependent) |

### 7.3 When chat storage is cleared

| Clears chat storage? |
|--------------------|
| **Reset chat** button → **Yes** |
| **Close tab** / close browser → **Yes** |
| **Logout** (logged-in user) → **Yes** |
| Close popup **X** → **No** |
| Browser refresh (same tab) → **No** (restores) |
| Minimize / navigate other pages on same SPA → **No** (typically) |

### 7.4 Speech bubble vs chat storage

| UI element | Dismiss ✕ | Affects chat history? |
|------------|-----------|------------------------|
| Launcher **speech bubble** | Hides bubble for tab (`spacey_bubble_dismissed`) | **No** |
| Popup **Reset chat** | Clears chat | **Yes** |
| Popup **close X** | Hides window only | **No** |

---

## 8. Behaviour checklist (optional reference)

A compact list of **documented behaviours** — not a mandatory test suite.

### Entry & shell

- Launcher visible on homepage / search (when data loaded)
- Launcher hidden on booking URL with `eventTypeId`
- Speech bubble appears (if not dismissed); bubble ✕ hides teaser only
- Logged-in greeting shows name / booking count when applicable
- Guest greeting does not require login

### Search & cards

- Type-only query returns cards & browse mode
- City refines results; chip shows location
- Budget refines; chip shows LKR cap
- Date switches to availability mode + Book Now
- Availability slots or seats when API sends data
- Card image / placeholder / booking opens in new tab
- Show 10 more appends cards when many results exist

### Chips

- Each chip ✕ triggers a new agent search
- Removing date returns browse mode
- Removing location expands to Sri Lanka
- Chips visible on empty result

### Agent behaviour

- Location-only → asks for type once
- Off-topic redirect
- Lists 9 types on request
- Human / agent → contact form + phone
- Try again on error
- Offline message when network off

### Persistence

- Close popup → reopen → same thread
- F5 same tab → same thread
- New tab → fresh chat
- Reset chat → fresh greeting
- Close tab → fresh chat in new session

---

## 9. Common misconceptions

| Assumption | Actual behaviour |
|------------|------------------|
| Identical bot wording every run | LLM varies phrasing |
| Space list duplicated in chat text | Cards carry the list; text is intro only |
| Spacey remembers you after **closing the tab** | Session is tab-scoped |
| “Available” before user gives a date | Browse mode — “Spaces You May Like” |
| Instant chip update without a new bot turn | ✕ triggers a full agent round-trip |
| Every card shows slot times | Depends on search API payload |
| Login required to search | Optional; only affects greeting context |

---

## 10. Environment & access

| Setting | Typical value |
|---------|----------------|
| `REACT_APP_USE_AGENT_V2` | `true` (V2 / Spacey) |
| Agent API | Gateway `…/api/search/agent` or local override (`REACT_APP_AGENT_URL`) |

If V2 is **false**, the legacy **rule-based** chatbot (`ChatbotPopup.js`) runs instead — not described in this document.

When reporting issues (e.g. empty cards, `/chat` errors), useful context includes: timestamp, user message, chips shown, same tab vs new tab, logged in vs guest, and network responses for `/chat` and search.

---

## 11. Quick reference — UI labels

| Label | Meaning |
|-------|---------|
| Spaces You May Like | Browse mode (no user date) |
| Available Spaces | Availability mode (user gave date) |
| View Details → | Browse — explore space, pick date on site |
| Book Now → | Availability — date pre-filled in URL |
| Thinking... | Waiting for agent API |
| Reset chat | Clear storage + new conversation |
| Show 10 more | Next page, same search |
| ✕ on chip | Remove one filter via new agent search |

---

*May 2026 — Spacey V2 (`ChatbotPopupV2.js`, session persistence, filter chips, browse/availability modes).*
