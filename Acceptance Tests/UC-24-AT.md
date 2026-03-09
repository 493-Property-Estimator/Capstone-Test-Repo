# Acceptance Test Suite — UC-24: Search by Address in the Map UI

## 1. Purpose
This acceptance test suite verifies that the map UI supports **address search** with suggestions and correctly navigates the map to the selected location, handling ambiguity, no-results, coverage limits, and dependency failures.

## 2. Scope
In scope:
- Search bar availability and usability
- Autocomplete suggestions (where supported)
- Submission of full address search
- Map pan/zoom to resolved coordinate
- Marker/highlight placement and address label display
- Handling ambiguous, invalid, no-result, and out-of-coverage searches
- Graceful behavior when geocoding service is unavailable

Out of scope:
- Estimate computation correctness

## 3. Assumptions and Test Data
- Supported browsers available.
- Geocoding service can be simulated to fail.
- Test inputs: `ADDR_UI_VALID`, `ADDR_UI_AMBIG`, `ADDR_UI_NONE`, `ADDR_UI_OOC`.

## 4. Entry and Exit Criteria
### Entry Criteria
- Map UI deployed and reachable.
- Geocoding/autocomplete services reachable.

### Exit Criteria
- All High priority tests pass.

## 5. Test Environment
- Web browser(s)
- Network access to map tiles/geocoding

---
## 6. Test Cases

### AT-UC24-001 — Search Bar Available
**Objective:** Verify the address search control is visible and enabled on map load.  
**Priority:** High

**Preconditions:**
- User can access the map UI

**Steps:**
1. Open the map UI landing page.

**Expected Results:**
- Search bar is visible and enabled.
- Search bar has placeholder/help text indicating expected input.

---

### AT-UC24-002 — Autocomplete Suggestions Appear
**Objective:** Verify suggestions appear as the user types.  
**Priority:** High

**Preconditions:**
- Map UI loaded
- Autocomplete service available

**Steps:**
1. Click into the search bar.
2. Type "10234 98 Str" into the field.
3. Wait 300ms for debounced autocomplete.

**Expected Results:**
- Dropdown suggestions appear with 3-5 matches:
  - "10234 98 Street NW, Edmonton, AB"
  - "10234 98 Street, Edmonton, AB"
  - Other close matches ordered by relevance
- Each suggestion shows full address with city
- UI indicates match confidence/type
- Loading indicator appears briefly if latency > 100ms

---

### AT-UC24-003 — Select Suggestion Navigates Map
**Objective:** Verify selecting a suggestion pans/zooms and drops a marker.  
**Priority:** High

**Preconditions:**
- Map UI loaded
- `ADDR_UI_VALID` has at least one suggestion

**Steps:**
1. Type `ADDR_UI_VALID` prefix until suggestions appear.
2. Click the correct suggestion.

**Expected Results:**
- Map pans and zooms to the selected location.
- Marker/highlight is placed.
- Canonical address label is displayed (if supported).

---

### AT-UC24-004 — Submit Full Address Without Clicking Suggestion
**Objective:** Verify pressing Enter triggers resolution and navigation.  
**Priority:** High

**Preconditions:**
- Map UI loaded
- Geocoder available

**Steps:**
1. Type full `ADDR_UI_VALID` into search bar.
2. Press Enter (or click search icon).

**Expected Results:**
- Map pans/zooms to resolved location.
- Marker/highlight appears.
- No error message displayed.

---

### AT-UC24-005 — Ambiguous Address Prompts Disambiguation
**Objective:** Verify ambiguous addresses show candidate choices.  
**Priority:** High

**Preconditions:**
- Map UI loaded
- `ADDR_UI_AMBIG` is known ambiguous

**Steps:**
1. Type and submit `ADDR_UI_AMBIG`.

**Expected Results:**
- System presents multiple candidate results.
- User can select one candidate to navigate.
- No silent auto-selection without indication.

---

### AT-UC24-006 — No Results Displays Clear Message
**Objective:** Verify no-match searches provide actionable feedback.  
**Priority:** High

**Preconditions:**
- Map UI loaded
- `ADDR_UI_NONE` yields no match

**Steps:**
1. Type and submit `ADDR_UI_NONE`.

**Expected Results:**
- UI displays 'No results found' (or equivalent).
- Map view remains unchanged.
- UI suggests alternate inputs if designed.

---

### AT-UC24-007 — Invalid Input Handling
**Objective:** Verify very short/invalid input shows guidance and debounces requests.  
**Priority:** Medium

**Preconditions:**
- Map UI loaded

**Steps:**
1. Enter a 1–2 character input (e.g., 'A').
2. Press Enter.

**Expected Results:**
- UI prompts user to enter more details.
- No excessive geocoding calls are made (debounced).

---

### AT-UC24-008 — Out-of-Coverage Address Handling
**Objective:** Verify out-of-coverage addresses produce a coverage warning.  
**Priority:** Medium

**Preconditions:**
- Map UI loaded
- `ADDR_UI_OOC` outside coverage

**Steps:**
1. Submit `ADDR_UI_OOC`.

**Expected Results:**
- UI indicates region is not supported.
- Map behavior follows spec (no change or boundary pan).

---

### AT-UC24-009 — Geocoding Service Unavailable
**Objective:** Verify graceful degradation when geocoding is down.  
**Priority:** High

**Preconditions:**
- Map UI loaded
- Ability to simulate geocoder outage

**Steps:**
1. Disable/interrupt geocoding service.
2. Submit `ADDR_UI_VALID`.

**Expected Results:**
- UI displays 'Search unavailable' (or similar).
- No infinite loading state.
- User can retry after service returns.

---

## 7. Traceability to UC-24 Scenario Narratives
- Happy path navigation: AT-UC24-003, AT-UC24-004
- Invalid/no-result/ambiguous coverage: AT-UC24-005, AT-UC24-006, AT-UC24-008
- Dependency failure: AT-UC24-009
