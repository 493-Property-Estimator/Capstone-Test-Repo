# Acceptance Test Suite — UC-32: Provide Clear Error Messages for Invalid Inputs

## 1. Purpose
This suite verifies developers receive actionable, consistent, and safe validation errors for invalid Estimate API requests.

## 2. Scope
In scope:
- Schema/type detection
- Field-level and multi-error reporting
- Status code semantics
- Redaction and consistency

## 3. Assumptions and Test Data
- Error schema defined and stable.
- Test payloads for missing fields, invalid coords, invalid polygons, unsupported formats, unresolvable addresses.

## 4. Entry and Exit Criteria

### Entry Criteria
- Estimate API deployed.
- Validation enabled.

### Exit Criteria
- All High priority tests pass.

## 5. Test Environment
- API test client

---
## 6. Test Cases

### AT-UC32-001 — Multi-error for Missing Fields
**Objective:** Verify all missing fields reported at once.  
**Priority:** High

**Preconditions:**
- Valid credentials

**Steps:**
1. Send payload missing property reference and required fields.

**Expected Results:**
- 400/422 returned.
- Errors array lists all missing fields with guidance.
- No estimate returned.

---

### AT-UC32-002 — Invalid Lat/Long Range Returns Clear Error
**Objective:** Verify coordinate bounds validation returns specific actionable errors.  
**Priority:** High

**Preconditions:**
- Valid API credentials

**Steps:**
1. Send POST /estimate with invalid coordinates:
```json
{
  "coordinates": {
    "lat": 91.5,
    "lng": -200.0
  }
}
```

**Expected Results:**
- HTTP 422 returned
- Response contains errors array with 2 items:
  - Error 1:
    - field: "coordinates.lat"
    - code: "value_out_of_range"
    - message: "Latitude must be between -90 and 90 degrees"
    - provided: 91.5
    - expected: "Number in range [-90, 90]"
  - Error 2:
    - field: "coordinates.lng"
    - code: "value_out_of_range"
    - message: "Longitude must be between -180 and 180 degrees"
    - provided: -200.0
    - expected: "Number in range [-180, 180]"
- No stack trace or internal error details exposed
- No estimate computed or returned

---

### AT-UC32-003 — Invalid Polygon Geometry
**Objective:** Verify geometry guidance for self-intersection.  
**Priority:** High

**Preconditions:**
- Valid credentials

**Steps:**
1. Send self-intersecting polygon.

**Expected Results:**
- 400/422 returned.
- Error explains geometry issue.
- Suggests correction.

---

### AT-UC32-004 — Unsupported Format
**Objective:** Verify unsupported formats list supported alternatives.  
**Priority:** High

**Preconditions:**
- Valid credentials

**Steps:**
1. Send unsupported property reference type.

**Expected Results:**
- 400 returned.
- Supported formats listed.

---

### AT-UC32-005 — Unresolvable Address Uses 422
**Objective:** Verify address not found returns 422 with suggestion.  
**Priority:** High

**Preconditions:**
- Valid credentials

**Steps:**
1. Send syntactically valid but non-existent address.

**Expected Results:**
- 422 returned.
- Suggestion to add postal code or use coords.

---

### AT-UC32-006 — Sensitive Value Redaction
**Objective:** Verify errors do not echo sensitive values.  
**Priority:** Medium

**Preconditions:**
- Valid credentials

**Steps:**
1. Send payload with long address; trigger validation error.

**Expected Results:**
- Field referenced but value redacted/truncated per policy.

---

### AT-UC32-007 — Schema Consistency Across Failures
**Objective:** Verify error schema consistent.  
**Priority:** Medium

**Preconditions:**
- Valid credentials

**Steps:**
1. Trigger missing fields error.
2. Trigger invalid coords error.
3. Trigger invalid polygon error.

**Expected Results:**
- Top-level schema consistent.
- Errors list consistent structure.

---

## 7. Traceability
- Multi-error and field guidance: AT-UC32-001 to AT-UC32-003
- Status semantics: AT-UC32-005
- Safety/consistency: AT-UC32-006, AT-UC32-007
