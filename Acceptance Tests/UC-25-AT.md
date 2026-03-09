# Acceptance Test Suite — UC-25: Toggle Open-Data Layers in the Map UI

## 1. Purpose
This suite verifies users can toggle open-data layers and that layers load/render/unload correctly with performance protections and graceful failures.

## 2. Scope
In scope:
- Layer toggle controls
- Data fetch per map bounds
- Overlay rendering and legend updates
- Progressive loading and debounce
- Partial coverage and API outage handling

Out of scope:
- Exact cartographic styling

## 3. Assumptions and Test Data
- Layers available: Schools, Parks, Census, Assessment Zones.
- Regions include dense and partial coverage areas.
- Ability to simulate Layer API outage/slowdown.

## 4. Entry and Exit Criteria

### Entry Criteria
- Map UI deployed.
- Layer API reachable.

### Exit Criteria
- All High priority tests pass.

## 5. Test Environment
- Browser UI
- Optional network throttling

---
## 6. Test Cases

### AT-UC25-001 — Layer Panel Availability
**Objective:** Verify layer toggles are visible and labeled.  
**Priority:** High

**Preconditions:**
- Map UI loaded

**Steps:**
1. Open map UI.
2. Locate layer panel/controls.

**Expected Results:**
- Layer toggles exist for expected layers.
- Toggles have readable names and default states.

---

### AT-UC25-002 — Enable Single Layer Renders Overlay
**Objective:** Verify enabling a layer fetches data and renders overlay with markers and legend.  
**Priority:** High

**Preconditions:**
- Map UI loaded
- Map centered on Edmonton (bounding box: 53.45°N to 53.65°N, -113.65°W to -113.35°W)
- Schools layer API available

**Steps:**
1. Navigate to dense region (Downtown Edmonton)
2. Click 'Schools' layer toggle in layer panel

**Expected Results:**
- Loading indicator appears briefly ("Loading schools...")
- After ~450ms, schools overlay appears with:
  - 127 school markers within map viewport
  - Markers use school icon (building/education symbol)
  - Different colors for elementary/high school types
- Legend panel updates with:
  - "Schools" entry
  - Icons showing elementary (blue) and high school (green)
  - Count: "127 schools visible"
- Clicking a school marker shows popup with name and type
- Map performance remains smooth (>30 FPS)

---

### AT-UC25-003 — Disable Layer Removes Overlay
**Objective:** Verify disabling a layer removes its overlay and legend entry.  
**Priority:** High

**Preconditions:**
- Schools layer enabled

**Steps:**
1. Disable 'Schools' layer.

**Expected Results:**
- Overlay removed.
- Legend entry removed/hidden.
- No residual markers remain.

---

### AT-UC25-004 — Multiple Layers Concurrently
**Objective:** Verify multiple layers can be enabled and remain distinguishable.  
**Priority:** High

**Preconditions:**
- Map UI loaded
- Layer API available

**Steps:**
1. Enable 'Parks' layer.
2. Enable 'Assessment Zones' layer.

**Expected Results:**
- Both overlays visible.
- Legend shows both.
- Toggling one doesn't affect other.

---

### AT-UC25-005 — Pan/Zoom Triggers Layer Refetch
**Objective:** Verify moving the map requests new data for current bounds.  
**Priority:** High

**Preconditions:**
- At least one layer enabled
- Layer API available

**Steps:**
1. Enable a layer.
2. Pan to adjacent region.
3. Zoom in/out within supported levels.

**Expected Results:**
- Overlay updates for new region.
- Requests are debounced (no excessive calls).

---

### AT-UC25-006 — Progressive Loading for Large Dataset
**Objective:** Verify large datasets load progressively and UI remains responsive.  
**Priority:** Medium

**Preconditions:**
- Map UI loaded
- Large layer available

**Steps:**
1. Enable a heavy layer (census boundaries).
2. Optionally throttle network.

**Expected Results:**
- UI shows loading state.
- Layer appears progressively.
- UI remains responsive.

---

### AT-UC25-007 — Rapid Toggle Debounce
**Objective:** Verify rapid toggles respect final state and avoid request spam.  
**Priority:** Medium

**Preconditions:**
- Map UI loaded
- Layer API available

**Steps:**
1. Rapidly toggle 'Schools' on/off several times.
2. Stop with 'Schools' ON.

**Expected Results:**
- Final state ON and overlay visible.
- No stuck spinners.
- Backend requests limited if measurable.

---

### AT-UC25-008 — Layer API Outage
**Objective:** Verify layer unavailable message on API failure.  
**Priority:** High

**Preconditions:**
- Map UI loaded
- Can simulate API outage

**Steps:**
1. Disable Layer API.
2. Enable a layer.

**Expected Results:**
- UI shows 'Layer unavailable'.
- Toggle reverts/disabled.
- No broken artifacts.

---

### AT-UC25-009 — Partial Coverage Warning
**Objective:** Verify incomplete coverage is communicated.  
**Priority:** Medium

**Preconditions:**
- Map UI loaded
- Region with partial layer coverage exists

**Steps:**
1. Navigate to partial-coverage region.
2. Enable affected layer.

**Expected Results:**
- Overlay renders available data.
- UI shows incomplete coverage warning.

---

## 7. Traceability
- Happy path toggle/render: AT-UC25-002, AT-UC25-003
- Degradation/performance: AT-UC25-006, AT-UC25-008, AT-UC25-009
