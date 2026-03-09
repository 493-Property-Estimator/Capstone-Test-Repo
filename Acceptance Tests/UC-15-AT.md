# Acceptance Tests — UC-15: Show top contributing factors

## Purpose
Verify that the system can explain *why* an estimate differs from the baseline by presenting a short, ranked list of top positive and negative contributing factors with human-readable labels and supporting values, and that it behaves safely when explanation data is missing or unsupported.

## References
* User Story: **US-15: Show top contributing factors**
* Use Case: `Use Cases/UC-15.md`
* Scenario: `Scenarios/SC-UC-15.md`
* Related Use Case: `Use Cases/UC-13.md` (point estimate)
* Related Use Case: `Use Cases/UC-14.md` (range, optional)

## Assumptions (minimal)
* The UI includes an “Explain”, “Details”, or “Why this value?” view accessible from an estimate result.
* The backend can return factor explanations for an estimate request, either inline with the estimate response or via a follow-up request keyed by a request/estimate identifier.
* Contribution magnitudes may be returned as dollar impacts or normalized scores; tests validate the chosen format is consistent and clearly labeled.

## Test Data Setup
Define controlled locations and configurations for repeatable tests:
* **L1 (Normal)**: Location with baseline and full feature availability; explanations expected.
* **L2 (Partial features)**: Location where at least one feature category is unavailable; explanations should be partial and flagged.
* **L3 (Attribution unsupported)**: Configuration/model variant where numeric attribution is not supported; qualitative explanation expected.
* **L4 (Explanation failure)**: Forced error/timeouts in the explainability service to verify graceful failure behavior.
* **L5 (Map-layer factor)**: Location where at least one top factor can be visualized on the map (e.g., nearby schools/parks).
* **L6 (Policy/filtered factor)**: Controlled case where a factor must be filtered/renamed due to product policy (if applicable).

## Acceptance Test Suite (Gherkin-style)

### AT-15-01 — Show ranked top contributing factors (happy path)
**Given** the user requests an estimate for **L1** and receives a point estimate and baseline metadata  
**When** the user opens “Why this value?”  
**Then** the UI displays a ranked list of contributing factors  
**And** the factors are separated into “Increases value” and “Decreases value” (or equivalent labels)  
**And** each factor has a human-readable name/label  
**And** each factor includes at least one supporting value when applicable (e.g., distance, count, category)  
**And** each factor shows an impact direction (+/–)  
**And** the list is limited to the configured “top N” factors (e.g., 3–5 each side) by default.

### AT-15-02 — Contributions align with the estimate relative to baseline (sanity check)
**Given** an explanation is displayed for **L1**  
**And** the baseline and point estimate are available  
**When** the user reviews the contributions  
**Then** the UI does not present contradictory signs (e.g., a factor listed under “Increases value” with a negative sign)  
**And** if numeric magnitudes are shown, the UI labels them clearly (e.g., “impact” or “contribution”) and applies consistent units/formatting.

### AT-15-03 — Factor labels and supporting values are readable and consistently formatted
**Given** explanations are displayed for **L1**  
**When** the UI renders factor items  
**Then** distances/units are displayed consistently (e.g., meters vs km)  
**And** numeric values use consistent rounding rules  
**And** factor names avoid highly technical jargon where a simpler label exists (or provide a definition/help affordance).

### AT-15-04 — Partial features returns partial explanations with missing-category warnings
**Given** the user requests an estimate for **L2** where some feature categories are unavailable  
**When** the user opens “Why this value?”  
**Then** the UI displays explanations for available factors  
**And** the UI indicates which categories are unavailable (e.g., “Crime data unavailable”)  
**And** missing categories are not shown as zero impact or neutral values  
**And** the UI preserves the estimate display even if explanations are partial.

### AT-15-05 — Attribution unsupported falls back to a qualitative explanation
**Given** the user requests an estimate under configuration **L3** where numeric attribution is not supported  
**When** the user opens “Why this value?”  
**Then** the UI displays a qualitative explanation (e.g., category-level signals)  
**And** the UI labels the explanation as qualitative (no numeric contribution claims)  
**And** the UI provides a brief note indicating the limitation (e.g., “Detailed contributions not available for this model”).

### AT-15-06 — Explainability service failure shows an explanation-unavailable state
**Given** the user requests an estimate for **L1**  
**And** the explainability service fails or times out (**L4**)  
**When** the user opens “Why this value?”  
**Then** the UI shows a user-friendly “Explanation unavailable” message  
**And** the estimate itself remains visible and unchanged  
**And** the UI offers a retry action (if supported)  
**And** the system does not crash or block other estimate interactions.

### AT-15-07 — Selecting a factor can highlight related map context (if supported)
**Given** the user views explanations for **L5**  
**And** at least one factor corresponds to a map layer (e.g., schools/parks)  
**When** the user selects that factor  
**Then** the UI highlights relevant map context (e.g., nearby POIs and/or distance)  
**And** the highlighted layer matches the selected factor’s category  
**And** dismissing the highlight returns the map to its prior state without losing the explanation panel.

### AT-15-08 — Non-visualizable factors do not break the map interaction
**Given** the user selects a factor that has no map visualization available  
**When** the user attempts to view it on the map  
**Then** the UI shows factor details but does not attempt to display an invalid layer  
**And** the UI indicates “Map view not available for this factor” (or equivalent) without failing.

### AT-15-09 — Policy filtering/renaming prevents prohibited or misleading factor presentation (if applicable)
**Given** the system is configured with policy-based filtering/renaming rules  
**And** the raw attribution output would include a prohibited/misleading factor (**L6**)  
**When** the user opens “Why this value?”  
**Then** the UI does not display prohibited factor labels as-is  
**And** the UI either omits the factor or displays an approved renamed label  
**And** if omission reduces explanation coverage materially, the UI displays a completeness note.

### AT-15-10 — Repeatability: same request yields consistent top factors for fixed versions
**Given** the user requests an estimate for **L1** multiple times  
**And** dataset versions and model/explainability configuration are unchanged between runs  
**When** the user opens “Why this value?” for each run  
**Then** the returned top factors and their ordering are consistent (allowing only for ties per defined tie-breaking rules)  
**And** supporting values and units remain consistent within rounding rules.

## Non-Functional Acceptance Criteria (verifiable)
* **Performance**: The explanation view loads within an agreed threshold (e.g., p95 ≤ 2s) when factors are precomputed/cached; otherwise meets the configured SLA.
* **Reliability**: If explanations cannot be computed, the system degrades gracefully (estimate remains available) with a clear message and optional retry.
* **Clarity/Transparency**: The UI avoids presenting contributions as definitive causal claims; labels/disclaimers make it clear these are model-derived explanations.

