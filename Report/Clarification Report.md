Clarification Report


UC-01:

## Question 1: Handling ambiguous/multiple address matches

  Context (Use Cases/UC-01.md, “Related Information → Open Issues”):
  “Handling of ambiguous or multiple address matches.”

  Why this is ambiguous: The flow doesn’t state what the system should do when
  geocoding returns multiple possible matches. Different choices affect user
  experience, error handling, and acceptance test design.

  Recommended: Option B — It minimizes incorrect estimates by letting the user
  choose the intended address when ambiguity exists, which aligns with a user-
  facing estimator and reduces silent errors.

  | Option | Description |
  |--------|-------------|
  | A | Automatically select the top geocoding match and proceed without user
  input |
  | B | Present a disambiguation list for the user to choose the correct address
  |
  | C | Treat multiple matches as a failure and ask the user to refine the
  address |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› b

• ## Question 2: Response time SLA for estimates

  Context (Acceptance Tests/UC-01-AT.md, AT-01 → Acceptance Criteria):
  “Response time meets the defined SLA (if applicable)”

  Why this is ambiguous: The SLA target isn’t defined. Different targets change
  performance requirements, test expectations, and potential architecture
  decisions.

  Recommended: Option B — p95 ≤ 3s balances usability expectations for a web
  estimator without over-constraining implementation.

  | Option | Description |
  |--------|-------------|
  | A | No SLA requirement (ignore performance target) |
  | B | p95 response time ≤ 3 seconds |
  | C | p95 response time ≤ 5 seconds |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› c

• ## Question 3: Handling repeated failed geocoding attempts

  Context (Scenarios/UC-01-Scenarios.md, “Alternative Path 6a -- Geocoding
  Failure or No Match”):
  “If the user abandons the process or repeated attempts fail, the use case ends
  in the Failed End Condition.”

  Why this is ambiguous: “Repeated attempts” is not defined. The cutoff affects
  UX flow and acceptance testing.

  Recommended: Option B — 3 attempts is a common, user-friendly threshold that
  avoids infinite loops while allowing recovery.

  | Option | Description |
  |--------|-------------|
  | A | 2 attempts max |
  | B | 3 attempts max |
  | C | 5 attempts max |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› b

• ## Question 4: Validation error message content

  Context (Acceptance Tests/UC-01-AT.md, AT-02 → Acceptance Criteria):
  “Error message is user-actionable (e.g., ‘Include street number and street
  name’)”

  Why this is ambiguous: The minimum content of “user-actionable” affects UX
  copy requirements and test assertions.

  Recommended: Option B — It keeps tests deterministic and ensures clear
  guidance for correction.

  | Option | Description |
  |--------|-------------|
  | A | Generic message only (e.g., “Invalid address”) |
  | B | Must mention missing components (street number + street name) |
  | C | Must show a concrete example address format |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› b



• ## Question 5: Interface scope (UI vs API)

  Context (Acceptance Tests/UC-01-AT.md, “Assumptions (for testability)”):
  “The system exposes an estimate UI or API that accepts a street address.”

  Why this is ambiguous: “UI or API” affects scope, test design, and controller/
  model boundaries. Implementing both vs UI-only changes behavior and artifacts.

  Recommended: Option A — The project constraints and user stories are UI-
  centric; requiring both would expand scope without evidence in the use case.

  | Option | Description |
  |--------|-------------|
  | A | UI only (web form + results) |
  | B | API only (no UI) |
  | C | Both UI and API |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.

c



UC-02:
## Question 1: Required coordinate precision

  Context (Use Cases/UC-02.md, “Related Information → Open Issues”):
  “Precision level required for coordinate input.”

  Why this is ambiguous: Precision affects validation, UI hints, and whether
  nearby points resolve to the same parcel/estimate. Different precision levels
  change test expectations.

  Recommended: Option B — 5 decimal places (~1.1 m) is a practical balance
  between accuracy and user burden for manual input.

  | Option | Description |
  |--------|-------------|
  | A | 4 decimal places (~11 m) |
  | B | 5 decimal places (~1.1 m) |
  | C | 6 decimal places (~0.11 m) |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› b


• ## Question 2: Handling coordinates between parcels

  Context (Use Cases/UC-02.md, “Related Information → Open Issues”):
  “Handling of coordinates that fall between parcels.”

  Why this is ambiguous: The choice affects canonical location ID selection and
  valuation behavior. Different rules can yield different estimates and test
  outcomes.

  Recommended: Option B — Selecting the nearest parcel is predictable, simple to
  explain, and minimizes user friction.

  | Option | Description |
  |--------|-------------|
  | A | Snap to parcel containing the point (if none, fail) |
  | B | Snap to nearest parcel centroid |
  | C | Return an error and require manual correction |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› B


• ## Question 3: Response time SLA for coordinate estimates

  Context (Acceptance Tests/UC-02-AT.md, AT-01 → Acceptance Criteria):
  “Response time meets SLA (if defined)”

  Why this is ambiguous: The SLA target isn’t defined. Different targets change
  performance requirements and test expectations.

  Recommended: Option B — p95 ≤ 5 seconds aligns with typical web estimate
  latency without over-constraining implementation.

  | Option | Description |
  |--------|-------------|
  | A | No SLA requirement (ignore performance target) |
  | B | p95 response time ≤ 5 seconds |
  | C | p95 response time ≤ 3 seconds |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› b


• ## Question 4: Interface scope (UI vs API)

  Context (Acceptance Tests/UC-02-AT.md, “Assumptions (for testability)”):
  “The system exposes an estimate UI or API that accepts latitude/longitude.”

  Why this is ambiguous: “UI or API” affects scope, test design, and controller/
  model boundaries.

  Recommended: Option A — The use case is user-facing, so UI-only keeps scope
  aligned unless API is explicitly required.

  | Option | Description |
  |--------|-------------|
  | A | UI only (web form + results) |
  | B | API only (no UI) |
  | C | Both UI and API |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› c


• ## Question 5: Behavior when coordinates are exactly on the boundary

  Context (Acceptance Tests/UC-02-AT.md, AT-06 → Given/When):
  “submitted coordinates … within global ranges … fall outside the supported
  geographic boundary”

  Why this is ambiguous: It doesn’t specify whether boundary lines are
  inclusive. This affects boundary validation and test cases.

  Recommended: Option A — Inclusive boundaries are the most common and simplest
  to explain.

  | Option | Description |
  |--------|-------------|
  | A | Boundary is inclusive (on-boundary is accepted) |
  | B | Boundary is exclusive (on-boundary is rejected) |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› a


UC-03:
## Question 1: Required click-to-coordinate precision

  Context (Use Cases/UC-03.md, “Related Information → Open Issues”):
  “Precision level of click-to-coordinate mapping.”

  Why this is ambiguous: Precision affects how close repeated clicks must be to
  count as “same location,” and it changes how canonical IDs and estimates are
  tested.

  Recommended: Option B — 5 decimal places (~1.1 m) balances accuracy with map
  click variability.

  | Option | Description |
  |--------|-------------|
  | A | 4 decimal places (~11 m) |
  | B | 5 decimal places (~1.1 m) |
  | C | 6 decimal places (~0.11 m) |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› b


• ## Question 2: Handling clicks between parcels

  Context (Use Cases/UC-03.md, “Related Information → Open Issues”):
  “Handling clicks that fall between parcels.”

  Why this is ambiguous: It affects how canonical location IDs and estimates are
  derived, and can change test expectations.

  Recommended: Option B — Snapping to the nearest parcel centroid is predictable
  and user-friendly.

  | Option | Description |
  |--------|-------------|
  | A | Snap to parcel containing the point (if none, fail) |
  | B | Snap to nearest parcel centroid |
  | C | Return an error and require the user to click again |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› b



• ## Question 3: Handling rapid repeated clicks (performance)

  Context (Use Cases/UC-03.md, “Related Information → Open Issues”):
  “Performance implications of rapid repeated clicks.”

  Why this is ambiguous: It affects request concurrency and UX responsiveness.
  Different policies change both behavior and testing.

  Recommended: Option B — Only the latest click result is shown, with prior
  requests canceled/ignored. This aligns with AT-07’s “most recent click”
  requirement.

  | Option | Description |
  |--------|-------------|
  | A | Queue all clicks and show each result in order |
  | B | Cancel/ignore prior clicks; only latest result renders |
  | C | Rate-limit clicks (e.g., 1 per second) |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› b

• ## Question 4: Boundary inclusion for map clicks

  Context (Acceptance Tests/UC-03-AT.md, AT-02 → Given/When):
  “click point is outside the supported geographic boundary”

  Why this is ambiguous: It doesn’t specify whether boundary lines are
  inclusive. This affects validation logic and tests for edge clicks.

  Recommended: Option A — Inclusive boundaries are the most common and simplest
  to explain.

  | Option | Description |
  |--------|-------------|
  | A | Boundary is inclusive (on-boundary is accepted) |
  | B | Boundary is exclusive (on-boundary is rejected) |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› a

• ## Question 5: Interface scope (UI vs API)

  Context (Acceptance Tests/UC-03-AT.md, “Assumptions (for testability)”):
  “The system provides an interactive map UI capable of returning click
  coordinates (lat/long or projected coords).”

  Why this is ambiguous: This implies UI, but doesn’t state whether an API is
  also required for coordinate submission. The scope impacts controller/model
  boundaries and test strategy.

  Recommended: Option A — The use case is explicitly map UI–driven, so UI-only
  keeps scope aligned.

  | Option | Description |
  |--------|-------------|
  | A | UI only (map interaction) |
  | B | API only (no UI) |
  | C | Both UI and API |
  | Short | Provide a different short answer (<=5 words) |

  You can reply with the option letter (e.g., “A”), accept the recommendation by
  saying “yes” or “recommended”, or provide your own short answer.


› c


UC-04:

 ## Question 1: Overlapping spatial units

  Source quote
  ./Use Cases/UC-04.md
  Section: ## Related Information

  > Handling of overlapping spatial units.

  Related execution line:
  ./Use Cases/UC-04.md
  Section: ## Main Success Scenario

  > 5. The system queries the spatial database to determine the corresponding
  > parcel, grid cell, or predefined spatial unit.

  Why this is ambiguous
  If multiple spatial units contain the same coordinates, the system needs one
  deterministic rule to pick the resolved unit. Different choices would produce
  different canonical location IDs and could change whether repeated
  normalizations stay stable.

  Recommended: Option A - It keeps the highest-resolution match first, which
  best aligns with parcel-first valuation behavior and minimizes ambiguity
  before fallback is needed.

  | Option | Description |
  |--------|-------------|
  | A | Prefer the most specific containing unit: parcel first, then other
  predefined units, then grid cell. |
  | B | Prefer a fixed unit type regardless of specificity: always use grid cell
  when overlaps exist. |
  | C | Reject overlapping matches as an error and stop normalization. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a

• ## Question 2: Canonical ID structure

  Source quote
  ./Use Cases/UC-04.md
  Section: ## Related Information

  > Definition and structure of canonical location ID (parcel-based vs grid-
  > based).

  Related requirement pressure from tests:
  ./Acceptance Tests/UC-04-AT.md
  Section: ## AT-01 --- Normalize address input to canonical location ID (Happy
  Path -- Address)

  > Canonical location ID follows defined format constraints (if any)

  Why this is ambiguous
  The system must generate a canonical location ID, but the source does not
  define whether the identifier format is parcel-oriented, grid-oriented, or
  type-prefixed. That choice affects ID generation, uniqueness rules, fallback
  behavior, and what tests should validate.

  Recommended: Option C - A type-prefixed canonical ID supports both parcel and
  fallback/grid-based resolution without changing the core contract that every
  input maps to one stable identifier.

  | Option | Description |
  |--------|-------------|
  | A | Canonical ID is always parcel-based; fallback units must be converted
  into a parcel-style identifier. |
  | B | Canonical ID is always grid-based; parcels are normalized into their
  containing grid cell identifier. |
  | C | Canonical ID is type-prefixed by resolved unit, such as parcel-based IDs
  for parcels and grid-based IDs for fallback/grid units. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› c

• ## Question 3: Fallback spatial unit choice

  Source quote
  ./Use Cases/UC-04.md
  Section: ## Extensions

  > 5a1: The system assigns the location to a fallback spatial unit (e.g., grid
  > cell).

  Supporting narrative:
  ./Scenarios/UC-04-Scenarios.md
  Section: ## Alternative Path 5a -- No Parcel or Spatial Unit Found

  > The system assigns the location to a fallback spatial unit, such as a grid
  > cell or nearest valid parcel, according to predefined rules.

  Why this is ambiguous
  The fallback rule directly affects which canonical ID is generated when no
  parcel is found. Choosing grid cell versus nearest valid parcel changes
  normalization outcomes, determinism rules, and what AT-05/AT-06 should
  validate.

  Recommended: Option A - Grid-cell fallback is the most consistent with the use
  case wording, avoids inventing parcel proximity rules, and keeps fallback
  deterministic with less spatial ambiguity.

  | Option | Description |
  |--------|-------------|
  | A | Always use a grid cell as the fallback spatial unit when no parcel or
  primary spatial unit is found. |
  | B | Always use the nearest valid parcel as the fallback spatial unit when no
  parcel or primary spatial unit is found. |
  | C | Use a configurable rule that may choose grid cell or nearest valid
  parcel depending on deployment settings. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a

UC-05:
## Question 1: Fallback averaging hierarchy

  Source quote
  ./Use Cases/UC-05.md
  Section: ## Related Information

  > Rules for fallback averaging hierarchy (parcel → grid → neighbourhood).

  Related fallback behavior:
  ./Use Cases/UC-05.md
  Section: ## Extensions

  > 4a1: The system attempts to compute an estimate using fallback spatial
  > averages (e.g., neighbourhood or grid-level averages).

  Supporting narrative:
  ./Scenarios/UC-05-Scenarios.md
  Section: ## Alternative Path 4a -- Baseline Assessment Data Unavailable

  > The system retrieves higher-level spatial averages, such as grid-level or
  > neighbourhood-level averages.

  Why this is ambiguous
  When baseline parcel-level data is missing, the system still needs a
  deterministic fallback source. Choosing grid first versus neighbourhood first
  changes the estimate produced, the warning metadata, and how AT-03 should be
  validated for consistent behavior.

  Recommended: Option A - Use grid-level averages first, then neighbourhood-
  level averages. Grid is typically more local and preserves more location
  specificity than neighbourhood aggregates, which reduces estimation drift
  while staying deterministic.

  | Option | Description |
  |--------|-------------|
  | A | Use grid-level averages first, then neighbourhood-level averages if grid
  data is unavailable. |
  | B | Use neighbourhood-level averages first, then grid-level averages if
  neighbourhood data is unavailable. |
  | C | Use whichever fallback source is available first, with no fixed
  priority. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a

• ## Question 2: Location-only uncertainty range rule

  Source quote
  ./Use Cases/UC-05.md
  Section: ## Related Information

  > Method for calculating uncertainty range with minimal input.

  Related behavior and test pressure:
  ./Use Cases/UC-05.md
  Section: ## Main Success Scenario

  > 6. The system computes a low/high estimate range reflecting uncertainty due
  > to limited input.

  ./Acceptance Tests/UC-05-AT.md
  Section: ## AT-06 --- Range reflects higher uncertainty for location-only
  (Business rule)

  > The location-only estimate range is equal to or wider than the standard-
  > input range

  Why this is ambiguous
  The sources require a wider or equal uncertainty range, but they do not define
  the rule used when a comparable standard-input estimate is not available at
  request time. Different interpretations would change both implementation
  behavior and what tests assert for range generation.

  Recommended: Option B - Define a fixed minimum widening rule for all location-
  only estimates, then still satisfy the comparison test when a standard-input
  benchmark exists. This keeps request-time behavior deterministic and testable
  without depending on a second live estimate.

  | Option | Description |
  |--------|-------------|
  | A | Compute a location-only range only by comparing against a standard-input
  estimate for the same location at runtime. |
  | B | Apply a fixed minimum widening rule to every location-only estimate, and
  require it to be at least as wide as any comparable standard-input range when
  both exist. |
  | C | Use the same range method as standard-input estimates and only widen it
  when baseline data is missing. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


• ## Question 3: Limited-input warning wording scope

  Source quote
  ./Use Cases/UC-05.md
  Section: ## Related Information

  > Clear UX messaging to prevent over-trust in location-only estimates.

  Related display requirements:
  ./Use Cases/UC-05.md
  Section: ## Main Success Scenario

  > 7. The system displays:
  > - A visible indication that the estimate is based on location-only input

  ./Scenarios/UC-05-Scenarios.md
  Section: ## Main Success Scenario -- Narrative

  > - A visible indication that the estimate is based on location-only input and
  > may have reduced accuracy

  Why this is ambiguous
  The use case requires a visible indication, but the source leaves room for
  whether the normal success path must always include both concepts: location-
  only and reduced accuracy, or whether reduced-accuracy wording is reserved for
  fallback data cases only. That changes UI copy, response metadata, and
  acceptance coverage.

  Recommended: Option B - Always show that the estimate is location-only, and
  reserve the stronger reduced-accuracy warning for fallback-data cases. This
  matches the main flow and keeps fallback warnings distinct instead of
  duplicating severity on every successful estimate.

  | Option | Description |
  |--------|-------------|
  | A | Every successful location-only estimate must always say both location-
  only and reduced accuracy. |
  | B | Every successful estimate must say location-only; reduced accuracy
  wording is additionally required when fallback data is used. |
  | C | Only fallback estimates need any warning; normal location-only estimates
  need no visible caution text. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b



UC-06:

• No critical ambiguities detected worth formal clarification.


UC-07:
##Question 1:
• Recommended: Option A - Omitting the desirability adjustment entirely matches
  the UC-07 exception flow verbatim and keeps downstream behavior simpler and
  easier to validate without inventing an extra neutral-score contract.

  Quoted ambiguity:

  - Use Cases/UC-07.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
    Use%20Cases/UC-07.md), Extensions, 2a2: “The system omits proximity features
    and proceeds without desirability adjustment.”
  - Acceptance Tests/UC-07-AT.md (/home/fronk/ECE493/Capstone/Group/
    ece493_2026w_group14/Acceptance%20Tests/UC-07-AT.md), AT-04 Then: “The
    system omits desirability adjustment (or sets to default neutral, per
    design)”

  Why this is ambiguous: these sources allow two materially different behaviors
  after coordinate-resolution failure. One omits the desirability value
  entirely; the other emits an explicit neutral default. That changes feature-
  set shape, downstream valuation behavior, and test assertions.

  | Option | Description |
  |--------|-------------|
  | A | Omit desirability adjustment entirely when coordinates cannot be
  resolved; no desirability value is attached. |
  | B | Set desirability to an explicit neutral default value when coordinates
  cannot be resolved, while still omitting proximity metrics. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


## Question 2:

• Recommended: Option A - Defaulting to routing-based distance aligns better
  with the use case’s valuation intent because it reflects real travel
  proximity, while the Euclidean path is already defined as the explicit
  fallback when routing fails.

  Quoted ambiguity:

  - Use Cases/UC-07.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
    Use%20Cases/UC-07.md), Preconditions: “Distance computation mechanisms
    (e.g., straight-line or routing-based) are available.”
  - Use Cases/UC-07.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
    Use%20Cases/UC-07.md), Related Information > Open Issues: “Whether to use
    straight-line or routing distance as default.”
  - Scenarios/UC-07-Scenarios.md (/home/fronk/ECE493/Capstone/Group/
    ece493_2026w_group14/Scenarios/UC-07-Scenarios.md), Main Success Scenario --
    Narrative: “Depending on system configuration, the distance may be computed
    using routing-based travel distance or straight-line (Euclidean) distance.”

  Why this is ambiguous: the default distance method changes the computed
  proximity metrics, desirability score, deterministic baselines, and what AT-
  01/AT-07 should treat as the normal path versus the fallback path in AT-03.

  | Option | Description |
  |--------|-------------|
  | A | Use routing-based distance by default; fall back to Euclidean only when
  routing fails. |
  | B | Use Euclidean distance by default; use routing only if explicitly
  configured. |
  | C | Use a single globally configured default method, with no required
  default in the spec. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a

## Question 3

• Recommended: Option A - Using one global search radius for all amenity
  categories keeps AT-01 through AT-07 simpler and more reproducible, while
  still matching the UC-07 requirement that a predefined search radius exists.

  Quoted ambiguity:

  - Use Cases/UC-07.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
    Use%20Cases/UC-07.md), Main Success Scenario, Step 3: “The system queries
    the spatial database for relevant amenities within a predefined search
    radius.”
  - Use Cases/UC-07.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
    Use%20Cases/UC-07.md), Related Information > Open Issues: “Definition of
    search radius per amenity category.”

  Why this is ambiguous: the phrase “a predefined search radius” suggests one
  shared radius, but the open issue explicitly raises per-category radii. That
  changes which schools, parks, and hospitals are included, which fallback path
  may trigger, and what deterministic test fixtures must assert.

  | Option | Description |
  |--------|-------------|
  | A | Use one shared search radius for all amenity categories. |
  | B | Use separate predefined search radii for each amenity category. |
  | C | Use one global default radius, with optional category-specific
  overrides. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a



UC-08:


## Question 1
Recommended: Option A - Omitting travel-based accessibility features entirely
  matches the UC-08 exception flow verbatim and keeps the failure path simpler
  and more consistent than introducing a neutral-default feature contract.

  Quoted ambiguity:

  - Use Cases/UC-08.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
    Use%20Cases/UC-08.md), Extensions, 2a2: “The system omits travel-based
    features and proceeds without accessibility adjustment.”
  - Acceptance Tests/UC-08-AT.md (/home/fronk/ECE493/Capstone/Group/
    ece493_2026w_group14/Acceptance%20Tests/UC-08-AT.md), AT-02 Then: “The
    system omits travel-based accessibility features (or sets neutral defaults
    per design)”

  Why this is ambiguous: these sources allow two materially different behaviors
  after property-coordinate resolution fails. One removes travel-based features
  entirely; the other emits explicit neutral defaults. That changes feature-set
  shape, downstream valuation handling, and exact test expectations for absence
  versus defaulted values.

  | Option | Description |
  |--------|-------------|
  | A | Omit travel-based accessibility features entirely when the canonical
  location ID cannot be resolved to coordinates. |
  | B | Set explicit neutral default travel-based accessibility features when
  the canonical location ID cannot be resolved to coordinates. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


## Question 2:

• Recommended: Option A - Using travel time as the primary metric better fits
  the accessibility intent and the routing-service use case, and it aligns with
  several UC-08 examples that already emphasize nearest travel time and average
  travel time.

  Quoted ambiguity:

  - Use Cases/UC-08.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
    Use%20Cases/UC-08.md), Main Success Scenario, Step 4: “The system invokes
    the routing service to compute travel distance (or travel time) along the
    road network between the property and each destination.”
  - Use Cases/UC-08.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
    Use%20Cases/UC-08.md), Related Information > Open Issues: “Travel time vs
    travel distance as primary metric.”
  - Scenarios/UC-08-Scenarios.md (/home/fronk/ECE493/Capstone/Group/
    ece493_2026w_group14/Scenarios/UC-08-Scenarios.md), Main Success Scenario --
    Narrative: “The system invokes the routing service to compute travel-based
    distances or travel times along the road network.”

  Why this is ambiguous: choosing time versus distance as the primary routing
  output changes the core feature values, aggregation formulas, sentinel policy,
  output units, and what downstream valuation consumes by default.

  | Option | Description |
  |--------|-------------|
  | A | Use travel time as the primary metric; distance may be secondary or
  supporting only. |
  | B | Use travel distance as the primary metric; time may be secondary or
  supporting only. |
  | C | Treat time and distance as equal primary outputs that must always both
  be computed and attached. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


## Question 3

• Recommended: Option A - A single default transport mode keeps routing results
  reproducible and aligns cleanly with UC-08’s need for deterministic
  accessibility features; car travel is the most common baseline for property-
  access valuation unless another domain rule says otherwise.

  Quoted ambiguity:

  - Use Cases/UC-08.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
    Use%20Cases/UC-08.md), Related Information > Open Issues: “Mode of transport
    assumptions (car, transit, walking).”
  - Acceptance Tests/UC-08-AT.md (/home/fronk/ECE493/Capstone/Group/
    ece493_2026w_group14/Acceptance%20Tests/UC-08-AT.md), AT-01 Given: “Routing
    service is available and configured (including transport mode)”
  - Acceptance Tests/UC-08-AT.md (/home/fronk/ECE493/Capstone/Group/
    ece493_2026w_group14/Acceptance%20Tests/UC-08-AT.md), AT-07 Given: “Same
    routing configuration (mode, weighting, time-of-day assumptions if any)”

  Why this is ambiguous: the chosen transport mode changes route availability,
  travel times, fallback behavior, and deterministic test expectations. Without
  a default, two compliant implementations could return materially different
  accessibility metrics for the same property and destinations.

  | Option | Description |
  |--------|-------------|
  | A | Use car travel as the default transport mode for routing. |
  | B | Use walking as the default transport mode for routing. |
  | C | Use transit as the default transport mode for routing. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


UC-09:


• ## Question 1: Geometry-resolution failure output

  Context:

  From Use Cases/UC-09.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-09.md), ## Extensions:

  > 2a2: The system omits green space computation and proceeds without
  > environmental adjustment.

  From Acceptance Tests/UC-09-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-09-AT.md), ## AT-02:

  > The system omits green space features (or sets neutral defaults per design)

  Why this is ambiguous: The use case says to omit computation and proceed,
  while the acceptance test allows two distinct output behaviors: omit the
  features entirely, or emit explicit neutral defaults. That changes output
  shape, traceability, and test assertions.

  Recommended: Option A - omit the green space features and mark them absent.
  This matches the use case text most directly and keeps failure handling
  simpler and less likely to imply computed values that were never actually
  derived.

  | Option | Description |
  |--------|-------------|
  | A | Omit green space features entirely and explicitly mark them absent. |
  | B | Return neutral default green space values instead of omitting features.
  |
  | C | Omit numeric features but include a status flag indicating environmental
  adjustment was skipped. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a

• ## Question 2: Green space category inclusion

  Context:

  From Use Cases/UC-09.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-09.md), ## Preconditions:

  > Land use or green space datasets (e.g., parks, forests, open spaces) are
  > available and indexed.

  From Use Cases/UC-09.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-09.md), ## Related Information / Open
  Issues:

  > Inclusion criteria for green space categories (public parks vs private green
  > land).

  From Scenarios/UC-09-Scenarios.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Scenarios/UC-09-Scenarios.md), ## Main Success Scenario
  -- Narrative:

  > Green space categories may include public parks, forests, recreational
  > fields, and other designated open spaces as defined by system rules.

  Why this is ambiguous: Different inclusion rules will change which polygons
  count toward area and coverage, so they directly change computed outputs and
  acceptance-test fixtures.

  Recommended: Option A - include only designated public or shared-access green
  spaces.
  This is the narrowest defensible rule, aligns best with environmental
  desirability as a user-facing amenity measure, and avoids overstating coverage
  with inaccessible private land.

  | Option | Description |
  |--------|-------------|
  | A | Count only public or shared-access green spaces such as parks, forests,
  and recreational fields. |
  | B | Count both public/shared-access green spaces and private green land if
  it is classified as green space in the dataset. |
  | C | Count any vegetated or open-space polygon regardless of access
  designation. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


UC-10:
## Question 1: Coordinate-resolution failure output

  Context:

  From Use Cases/UC-10.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-10.md), ## Extensions:

  > 2a2: The system omits school distance computation and proceeds without
  > family suitability adjustment.

  From Acceptance Tests/UC-10-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-10-AT.md), ## AT-02:

  > The system omits school distance metrics and family suitability adjustment
  > (or sets neutral defaults per design)

  Why this is ambiguous: The use case points to omission, while the acceptance
  test allows either omission or explicit neutral defaults. That changes output
  shape, metadata, and the assertions needed in tests.

  Recommended: Option A - omit school features and explicitly mark them absent.
  This matches the use case text directly and avoids implying computed values
  where no coordinates were available.

  | Option | Description |
  |--------|-------------|
  | A | Omit school distance metrics and suitability output, and explicitly mark
  them absent. |
  | B | Return neutral default school metrics and suitability values instead of
  omitting them. |
  | C | Omit numeric metrics but include a status flag showing school proximity
  was skipped. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


• ## Question 2: School category scope

  Context:

  From Use Cases/UC-10.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-10.md), ## Preconditions:

  > School dataset (e.g., elementary, middle, high schools) is available and
  > indexed.

  From Use Cases/UC-10.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-10.md), ## Main Success Scenario / Step 5:

  > Distance to nearest elementary school
  > Distance to nearest secondary school

  From Use Cases/UC-10.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-10.md), ## Related Information / Open
  Issues:

  > School category granularity (public vs private, catchment zones).

  From Acceptance Tests/UC-10-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-10-AT.md), ## Assumptions:

  > School dataset can be mocked with known school points and categories
  > (elementary/middle/high or "secondary").

  Why this is ambiguous: The sources define category levels, but they do not say
  whether private schools count, whether middle/high should be merged into
  “secondary,” or whether catchment rules exclude some schools. That directly
  changes which schools are queried and which metrics appear.

  Recommended: Option A - include all schools in the dataset, grouped into
  elementary and secondary for metrics.
  This best matches the use case’s required metrics while avoiding extra policy
  assumptions like catchment eligibility that are not in scope.

  | Option | Description |
  |--------|-------------|
  | A | Include all schools in the dataset and map them into elementary and
  secondary metric groups. |
  | B | Include only public schools and map them into elementary and secondary
  metric groups. |
  | C | Include only schools eligible by catchment rules for the property. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


UC-11:
## Question 1: Coordinate-resolution failure output

  Context:

  From Use Cases/UC-11.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-11.md), ## Extensions:

  > 2a2: The system omits commute accessibility computation and proceeds without
  > work-access adjustment.

  From Acceptance Tests/UC-11-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-11-AT.md), ## AT-02:

  > The system omits commute features (or sets neutral defaults per design)

  Why this is ambiguous: The use case says to omit commute computation, while
  the acceptance test allows either omission or explicit neutral defaults. That
  changes output shape, metadata, and test assertions.

  Recommended: Option A - omit commute features and explicitly mark them absent.
  This matches the use case most directly and avoids implying computed work-
  access values when coordinates were unavailable.

  | Option | Description |
  |--------|-------------|
  | A | Omit commute metrics and accessibility indicator, and explicitly mark
  them absent. |
  | B | Return neutral default commute metrics and accessibility values instead
  of omitting them. |
  | C | Omit numeric commute metrics but include a status flag indicating work-
  access computation was skipped. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


• ## Question 2: Empty-target output policy

  Context:

  From Use Cases/UC-11.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-11.md), ## Extensions:

  > 3a1: The system records default or neutral commute accessibility values
  > according to predefined rules.

  From Scenarios/UC-11-Scenarios.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Scenarios/UC-11-Scenarios.md), ## Alternative Path 3a --
  No Employment Centers Configured or Found:

  > This may include: - Assigning neutral accessibility scores
  > - Recording zero-count employment centers

  From Acceptance Tests/UC-11-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-11-AT.md), ## AT-03:

  > The system records default/neutral commute accessibility values per policy
  > (e.g., neutral index, null/empty metrics)

  Why this is ambiguous: The sources require a deterministic empty-target
  policy, but they do not define whether the output should contain neutral
  computed values, null/empty commute metrics, or both. That changes output
  shape and exact acceptance-test fixtures.

  Recommended: Option A - return a neutral accessibility indicator with empty
  commute metrics and zero target count.
  This preserves a deterministic output without inventing travel values for
  targets that do not exist, and it aligns with the scenario narrative’s zero-
  count handling.

  | Option | Description |
  |--------|-------------|
  | A | Return a neutral accessibility indicator, empty or null commute metrics,
  and zero target count. |
  | B | Return neutral/default numeric commute metrics plus a neutral
  accessibility indicator. |
  | C | Return only a status marker indicating no employment centers were
  available, without commute metrics or indicator. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


UC-12:
## Question 1: Coordinate-resolution failure output

  Context:

  From Use Cases/UC-12.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-12.md), ## Extensions:

  > 2a2: The system omits neighbourhood computation and proceeds without context
  > features.

  From Acceptance Tests/UC-12-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-12-AT.md), ## AT-02:

  > The system omits neighbourhood indicators and composite profile (or sets
  > neutral defaults per design)

  Why this is ambiguous: The use case points to omission, while the acceptance
  test allows either omission or explicit neutral defaults. That changes output
  shape, metadata, and the exact assertions used in tests.

  Recommended: Option A - omit neighbourhood features and explicitly mark them
  absent.
  This matches the use case most directly and avoids implying computed local-
  context values when coordinates were unavailable.

  | Option | Description |
  |--------|-------------|
  | A | Omit neighbourhood indicators and composite profile, and explicitly mark
  them absent. |
  | B | Return neutral default indicators and a neutral composite profile
  instead of omitting them. |
  | C | Omit indicator values but include a status flag indicating neighbourhood
  computation was skipped. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


• ## Question 2: Boundary-resolution policy

  Context:

  From Use Cases/UC-12.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-12.md), ## Extensions:

  > 3a1: The system applies nearest-boundary or centroid-based assignment logic.

  From Scenarios/UC-12-Scenarios.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Scenarios/UC-12-Scenarios.md), ## Alternative Path 3a --
  Property Does Not Map Cleanly to a Neighbourhood Boundary:

  > This may include: - Assigning the property to the nearest neighbourhood
  > centroid
  > - Selecting the boundary with the largest area overlap
  > - Applying deterministic tie-breaking rules

  From Acceptance Tests/UC-12-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-12-AT.md), ## AT-03:

  > Boundary resolution policy is configured (e.g., nearest-centroid, largest-
  > overlap, deterministic tie-break rule)

  Why this is ambiguous: The sources require a deterministic configured policy,
  but the current spec hard-codes only nearest-boundary or centroid-based
  assignment logic. Different policies can select different neighbourhoods,
  which changes indicator values and test outcomes.

  Recommended: Option B - support whichever configured deterministic policy is
  active.
  This aligns with the acceptance test and scenario narrative, which explicitly
  treat the resolution policy as configurable rather than fixed to one method.

  | Option | Description |
  |--------|-------------|
  | A | Always use nearest-centroid assignment for ambiguous boundary cases. |
  | B | Apply the configured deterministic policy, such as nearest-centroid,
  largest-overlap, or a deterministic tie-break rule. |
  | C | Always use largest-overlap assignment for ambiguous boundary cases. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


UC-13:
## Question 1: Missing Baseline Policy

  Recommended: Option A - Use nearest-neighbour baseline. It preserves the
  estimate flow for more requests while staying aligned with the use case’s
  stated fallback examples and keeps behavior deterministic for testing.

  Source quote
  From ./Use Cases/UC-13.md, section ## Extensions:

  > 5a: Assessment baseline not found for the normalized location
  >
  > - 5a1: The system applies the defined fallback (e.g., nearest-neighbour
  >   assessment baseline, neighbourhood median baseline, or “baseline
  >   unavailable” mode).

  From ./Use Cases/UC-13.md, section ## Related Information:

  > - Baseline fallback policy when assessment records are missing or ambiguous.

  From ./Acceptance Tests/UC-13-AT.md, section ### AT-13-06 — Missing baseline
  uses configured fallback and is flagged:

  > Then the system returns one estimated_value (if fallback policy allows
  > estimation)

  Why this is ambiguous
  The sources require a fallback policy, but they do not define which policy is
  in force. Different choices change implementation behavior and expected test
  outcomes:

  - whether an estimate is returned at all for L4
  - what baseline source is used
  - what warning text/metadata is required

  | Option | Description |
  |--------|-------------|
  | A | Use the nearest-neighbour assessment baseline and return an estimate
  with a missing-baseline warning. |
  | B | Use a neighbourhood median baseline and return an estimate with a
  missing-baseline warning. |
  | C | Do not estimate when the baseline is missing; return a no-estimate
  result with a user-facing warning/error. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a



• ## Question 2: Request Tracing Exposure

  Recommended: Option B - Allow tracing by either returning the identifier in
  the successful response or logging one tied to the client session. That
  matches the acceptance test exactly and avoids over-constraining the feature
  beyond the source material.

  Source quote
  From ./Acceptance Tests/UC-13-AT.md, section ### AT-13-11 — API response
  contains request tracing information for support/debugging (if supported):

  > Then the response includes a correlation/request identifier (e.g.,
  > request_id) or the system logs one that can be tied to the client session

  From ./Use Cases/UC-13.md, section ## Extensions:

  > - 7a: Valuation engine fails (internal error)
  >     - 7a1: The system logs the error with correlation IDs and returns a
  >       user-friendly message indicating the estimate could not be produced.

  Why this is ambiguous
  The sources require request tracing support, but they do not fix whether the
  identifier must be exposed directly in successful API responses or only
  guaranteed in server-side logging tied to the session. That changes response
  shape and test assertions.

  | Option | Description |
  |--------|-------------|
  | A | Always include a correlation/request identifier in every successful
  estimate response. |
  | B | Support either behavior: include the identifier in the response, or log
  one tied to the client session. |
  | C | Log the identifier only; do not expose it in successful responses. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


• ## Question 3: Canonical Location Choice

  Recommended: Option A - Use the parcel-associated location when parcel and
  clicked point differ. The use case flow is baseline-first around parcel/
  assessment lookup, so parcel association gives the most stable behavior for
  baseline retrieval and repeatable tests.

  Source quote
  From ./Use Cases/UC-13.md, section ## Main Success Scenario:

  > 4. The system normalizes the input to a canonical location ID and resolves a
  >    representative point/geometry for feature computation.

  From ./Use Cases/UC-13.md, section ## Main Success Scenario:

  > 5. The system retrieves the assessment baseline value for the canonical
  >    location (or nearest applicable parcel/assessment unit) and records the
  >    baseline metadata (assessment year, source).

  From ./Use Cases/UC-13.md, section ## Related Information:

  > - Definition of the “canonical location ID” when parcels and points differ
  >   (parcel centroid vs. clicked point).

  Why this is ambiguous
  The use case requires a canonical location ID and representative geometry, but
  it does not define which source wins when a user-selected point and parcel
  association disagree. That changes normalization results, baseline lookup
  behavior, feature computation inputs, and repeatability expectations.

  | Option | Description |
  |--------|-------------|
  | A | Canonicalize to the parcel-associated location; use the parcel as the
  authoritative location when point and parcel differ. |
  | B | Canonicalize to the clicked point; use parcel association only as
  supporting context for baseline lookup. |
  | C | Reject mismatches and require the user to confirm or reselect the
  location before estimation. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


UC-14:

## Question 1: Range Failure Behavior

  Recommended: Option A - Degrade gracefully to point estimate only with a
  warning. That matches the acceptance-test assumptions, preserves the core
  estimate result for the user, and reduces failure impact without changing the
  point-estimate flow.

  Source quote
  From ./Use Cases/UC-14.md, section ## Failed End Condition:

  > - The system cannot provide an uncertainty range (and either returns only a
  >   point estimate with a warning, or fails the request based on product
  >   requirements).

  From ./Use Cases/UC-14.md, section ## Extensions:

  > - 3b: Range computation fails due to internal error
  >     - 3b1: The system logs the error and returns only the point estimate
  >       (preferred) or a failure response (if range is mandatory).

  From ./Acceptance Tests/UC-14-AT.md, section ## Assumptions (minimal):

  > - If range computation fails, the product either (a) degrades gracefully to
  >   point estimate only with a warning, or (b) fails the request; these tests
  >   assume graceful degradation unless explicitly configured otherwise.

  Why this is ambiguous
  The sources allow two different product behaviors when range computation
  fails. That changes API behavior, UI behavior, and test expectations for
  failure scenarios.

  | Option | Description |
  |--------|-------------|
  | A | Always degrade gracefully: return the point estimate with a range-
  unavailable warning. |
  | B | Treat the range as mandatory: fail the full request if the range cannot
  be computed. |
  | C | Make it configurable per environment or product setting. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


• ## Question 2: Range Type / Interval Level

  Recommended: Option C - Make the interval level configurable and expose that
  configured value consistently in API metadata and UI text. The sources require
  consistency with product configuration but do not mandate one fixed interval,
  so this resolves the ambiguity without over-constraining the feature.

  Source quote
  From ./Use Cases/UC-14.md, section ## Related Information:

  > - Definition of the range type (e.g., 80% vs 90% vs 95% interval) and how it
  >   is explained in the UI.

  From ./Acceptance Tests/UC-14-AT.md, section ## Test Data Setup:

  > - The configured interval level/type (e.g., 80%/90%/95% band) is known for
  >   the environment under test so the UI label and metadata can be verified.

  From ./Acceptance Tests/UC-14-AT.md, section ### AT-14-09 — Range metadata is
  present and consistent with product configuration:

  > Given the system is configured to use a specific range type/interval level
  > Then the API response includes metadata that identifies the range type/level
  > (as configured)
  > And the UI label/help text matches that configuration (no conflicting
  > interval claims).

  Why this is ambiguous
  The sources require a defined range type/level, but they do not specify which
  interval level is the product standard. That changes returned metadata, UI
  wording, and test fixtures.

  | Option | Description |
  |--------|-------------|
  | A | Standardize on an 80% interval for all environments. |
  | B | Standardize on a 90% interval for all environments. |
  | C | Keep the interval level configurable and require the response and UI to
  reflect the configured value. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› c


• ## Question 3: Too-Wide Range Guardrail

  Recommended: Option C - Use a configurable maximum width limit and, if
  exceeded, adjust the range and warn. The sources explicitly mention configured
  limits in testing and “too-wide” guardrails as an open issue, so a
  configurable limit is the least brittle and most testable choice.

  Source quote
  From ./Use Cases/UC-14.md, section ## Exception/Error Flows:

  > - 4a: The computed range is invalid (low > high, negative low, unreasonably
  >   wide)
  >     - 4a1: The system clamps and/or recomputes using a safe fallback band.

  From ./Use Cases/UC-14.md, section ## Related Information:

  > - Guardrails for “too-wide” ranges and how to communicate low confidence to
  >   the user.

  From ./Acceptance Tests/UC-14-AT.md, section ### AT-14-06 — Guardrails prevent
  invalid ranges and are transparent:

  > - range width respects configured limits (if any)

  Why this is ambiguous
  The sources require guardrails for unreasonably wide ranges, but they do not
  define what counts as too wide or whether a fixed or configurable threshold is
  used. That changes validation logic and guardrail test setup.

  | Option | Description |
  |--------|-------------|
  | A | Use a fixed product-wide maximum width rule for all ranges. |
  | B | Do not enforce a width cap; only fix ordering and negative lows. |
  | C | Use a configurable maximum width limit and adjust or recompute the range
  when exceeded. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› c


UC-15:
## Question 1: Contribution Magnitude Format

  Recommended: Option C - Support either dollar impacts or normalized scores,
  but require one configured format to be used consistently and clearly labeled
  for a given environment. That matches the acceptance tests and use case
  without forcing a product decision the sources intentionally leave open.

  Source quote
  From ./Use Cases/UC-15.md, section ## Main Success Scenario:

  > 6. The system formats each factor into a user-friendly explanation item:
  >
  > - impact direction (+/–) and magnitude (absolute or relative, depending on
  >   product decision)

  From ./Use Cases/UC-15.md, section ## Related Information:

  > - Exact algorithm for contributions and whether to expose absolute dollar
  >   impacts or normalized scores.

  From ./Acceptance Tests/UC-15-AT.md, section ## Assumptions (minimal):

  > - Contribution magnitudes may be returned as dollar impacts or normalized
  >   scores; tests validate the chosen format is consistent and clearly
  >   labeled.

  Why this is ambiguous
  The sources allow more than one contribution-magnitude format, but they do not
  define which format is the product standard. That changes API payload shape,
  UI labels, and test assertions for displayed factor magnitudes.

  | Option | Description |
  |--------|-------------|
  | A | Always show contribution magnitudes as absolute dollar impacts. |
  | B | Always show contribution magnitudes as normalized scores. |
  | C | Allow either format by configuration, but require the configured format
  to be consistent and clearly labeled. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› c


• ## Question 2: Default Number of Factors

  Recommended: Option C - Keep the default top-N count configurable, with the UI
  limited to that configured value by default. The sources explicitly frame this
  as a product decision and the acceptance test only requires a configured
  default, so this preserves flexibility without changing behavior contracts.

  Source quote
  From ./Use Cases/UC-15.md, section ## Main Success Scenario:

  > 5. The system ranks the contributions and selects the top contributors
  >    (e.g., top 3–5 increases and top 3–5 decreases).

  From ./Use Cases/UC-15.md, section ## Related Information:

  > - How many factors to show by default and whether the user can expand for
  >   more.

  From ./Acceptance Tests/UC-15-AT.md, section ### AT-15-01 — Show ranked top
  contributing factors (happy path):

  > And the list is limited to the configured “top N” factors (e.g., 3–5 each
  > side) by default.

  Why this is ambiguous
  The sources require a default top-N limit, but they do not define the default
  count. That changes UI content volume, ranking cutoffs, and test fixtures.

  | Option | Description |
  |--------|-------------|
  | A | Default to top 3 increases and top 3 decreases. |
  | B | Default to top 5 increases and top 5 decreases. |
  | C | Keep the top-N count configurable and enforce that configured default in
  the UI. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› c


• ## Question 3: Map-Layer Support Scope

  Recommended: Option B - Make map highlighting available only for factors that
  have mapped context, and show a clear unavailable state for the rest. That
  aligns with the use case, scenario, and acceptance tests without forcing every
  factor to be visualizable.

  Source quote
  From ./Use Cases/UC-15.md, section ## Main Success Scenario:

  > 7. The UI displays the ranked list, clearly separating “increases value” vs.
  >    “decreases value”, and provides access to related map layers when
  >    applicable (e.g., show nearby schools/parks).

  From ./Use Cases/UC-15.md, section ## Related Information:

  > - UI requirements for mapping factors to layers (e.g., clicking “Schools”
  >   highlights nearby schools).

  From ./Acceptance Tests/UC-15-AT.md, section ### AT-15-07 — Selecting a factor
  can highlight related map context (if supported):

  > Given at least one factor corresponds to a map layer
  > When the user selects that factor
  > Then the UI highlights relevant map context

  From ./Acceptance Tests/UC-15-AT.md, section ### AT-15-08 — Non-visualizable
  factors do not break the map interaction:

  > Given the user selects a factor that has no map visualization available
  > Then the UI indicates “Map view not available for this factor” (or
  > equivalent) without failing.

  Why this is ambiguous
  The sources require map highlighting when applicable, but they do not define
  whether map support is expected broadly for most factors or only selectively
  for factors with natural spatial context. That changes UI affordances and test
  setup for factor interaction.

  | Option | Description |
  |--------|-------------|
  | A | Every displayed factor must offer a map interaction, even if some only
  show a generic placeholder. |
  | B | Only factors with real map context offer map highlighting; non-
  visualizable factors show a clear unavailable state. |
  | C | Disable map integration for this feature and show factor details only. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


UC-16:
No critical ambiguities detected worth formal clarification.


UC-17:
No critical ambiguities detected worth formal clarification.


UC-18:
• No critical ambiguities detected worth formal clarification


UC-19:
## Question 1: Invalid assessment records policy

  Source quote

  From Use Cases/UC-19.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-19.md#L24) Main Success Scenario, step 5:

  > handles missing/invalid entries according to rules (drop, quarantine, or
  > null)

  From Acceptance Tests/UC-19-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-19-AT.md#L54) AT-19-04:

  > Then the system fails the run or quarantines invalid records according to
  > policy

  Why this is ambiguous

  The sources require a policy, but they do not define which policy applies for
  UC-19. This changes implementation and test behavior in a material way:

  - whether invalid rows are retained separately or discarded
  - whether the run can still succeed with some bad rows present
  - what QA thresholds and reporting behavior must be implemented

  Recommended: Option B - quarantine invalid rows and continue unless invalid-
  rate QA fails. This preserves auditability, matches the scenario language
  around quarantining and reporting counts/examples, and avoids silently losing
  source data.

  | Option | Description |
  |--------|-------------|
  | A | Fail the entire run on any invalid required-value record; no partial
  ingest allowed. |
  | B | Quarantine invalid rows, continue processing valid rows, and block
  promotion only if invalid-rate QA exceeds threshold. |
  | C | Drop invalid rows immediately, continue processing valid rows, and
  report only aggregate rejection counts. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


• ## Question 2: Duplicate mapping resolution precedence

  Source quote

  From Use Cases/UC-19.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-19.md#L29) Main Success Scenario, step 8:

  > duplicates: multiple records mapping to the same canonical location handled
  > per rule (latest year, highest confidence match)

  From Acceptance Tests/UC-19-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-19-AT.md#L89) AT-19-08:

  > Then the system applies a deterministic resolution rule (e.g., highest
  > confidence match; preferred record type; latest year when multiple years
  > ingested)

  Why this is ambiguous

  The sources require a deterministic duplicate-resolution rule, but they do not
  define which criterion takes precedence when multiple records map to the same
  canonical location ID. This changes implementation and test outcomes because
  different rules can select different retained baseline values for the same
  inputs.

  Recommended: Option A - highest confidence match first, then latest year if
  multiple years are present. This aligns with the source emphasis on linking
  quality, keeps same-year duplicate resolution stable, and uses year only when
  it is actually relevant.

  | Option | Description |
  |--------|-------------|
  | A | Prefer highest confidence match first; use latest year only when
  duplicates span multiple years. |
  | B | Prefer latest year first whenever years differ; use highest confidence
  only as a tie-breaker within the same year. |
  | C | Prefer a configured record type priority first, then highest confidence,
  then latest year. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a

UC-20:

## Question 1: Conflict detection scope for identical raw labels

  Source quote

  From Use Cases/UC-20.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-20.md#L27) Main Success Scenario, step 5:

  > detection of conflicting mappings (same raw label mapped to multiple
  > canonical categories)

  From Acceptance Tests/UC-20-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-20-AT.md#L86) AT-20-07:

  > Given mappings for P3 cause the same raw label to map to multiple canonical
  > categories

  Why this is ambiguous

  The sources require conflict detection, but they do not say whether "same raw
  label" is evaluated:

  - globally across all sources, or
  - within each source separately.

  That changes mapping-rule structure, QA behavior, and what counts as a
  blocking conflict.

  Recommended: Option B - treat conflicts as source-scoped by default. Different
  data providers often reuse the same label with different semantics, so scoping
  by source reduces false positives while still allowing explicit cross-source
  normalization through mapping rules.

  | Option | Description |
  |--------|-------------|
  | A | A raw label must map to one canonical category globally across all
  sources. |
  | B | A raw label must map consistently within each source; the same label may
  map differently in different sources. |
  | C | Use a hybrid rule: global by default, but allow explicit source-specific
  overrides. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


• ## Question 2: Permissive-governance behavior for mapping conflicts

  Source quote

  From Use Cases/UC-20.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-20.md#L10) Failed End Condition:

  > Category standardization fails or produces incomplete/incorrect mappings;
  > POIs are not promoted, or they are promoted with explicit “unmapped”
  > categories and warnings based on governance policy.

  From Use Cases/UC-20.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-20.md#L38) Extensions, 5a:

  > Mapping quality below threshold (too many unmapped POIs)
  > 5a1: The system blocks promotion or promotes with warnings based on
  > governance policy.

  From Acceptance Tests/UC-20-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-20-AT.md#L86) AT-20-07:

  > And governance policy is Strict
  > Then QA fails due to conflicts exceeding threshold
  > And promotion is blocked

  Why this is ambiguous

  The sources clearly define strict-mode behavior for conflicts, and they define
  policy-driven behavior for unmapped-rate thresholds. They do not clearly say
  whether conflicts may ever be promoted under permissive governance, or whether
  conflicts always block promotion regardless of policy. That changes QA logic
  and test expectations for non-strict runs.

  Recommended: Option A - conflicts always block promotion, while permissive
  governance applies only to unmapped-rate thresholds. Conflicting canonical
  assignments create semantic inconsistency that is riskier than unmapped labels
  and is harder for downstream consumers to interpret safely.

  | Option | Description |
  |--------|-------------|
  | A | Conflicts always block promotion; permissive governance only affects
  unmapped-threshold handling. |
  | B | Under permissive governance, conflicts may also be promoted with
  explicit warnings and conflict flags. |
  | C | Conflicts may be promoted only if they stay below a separate conflict
  threshold in permissive mode. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a

UC-21:
## Question 1: Meaning of “low-confidence” review behavior

  Source quote

  From Use Cases/UC-21.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-21.md#L31) Main Success Scenario, step 6:

  > The system flags low-confidence candidates for review and does not merge
  > them automatically (or merges only with strict rules, depending on policy).

  From Acceptance Tests/UC-21-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-21-AT.md#L52) AT-21-03:

  > And medium-confidence matches are placed into a review list and are not
  > merged silently
  > And low-confidence matches are not merged.

  Why this is ambiguous

  The use case suggests low-confidence candidates may be reviewed or even merged
  under a policy, but the acceptance test fixes a three-band model where medium-
  confidence goes to review and low-confidence does not merge. This changes
  data-model shape, review-list contents, and scoring-threshold implementation.

  Recommended: Option B - medium confidence goes to review; low confidence is
  rejected and not added to the review list by default. This matches the
  acceptance tests directly and keeps the review queue focused on genuinely
  borderline cases.

  | Option | Description |
  |--------|-------------|
  | A | Low-confidence candidates also go to the review list, but are never
  auto-merged. |
  | B | Medium-confidence candidates go to review; low-confidence candidates are
  rejected and not reviewed by default. |
  | C | Low-confidence candidates may be merged under a separate strict-policy
  mode. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b



• ## Question 2: Precedence order for conflicting source attributes

  Source quote

  From Use Cases/UC-21.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-21.md#L38) Extensions, 5a:

  > 5a1: The system applies precedence rules (preferred source, latest update,
  > higher-quality dataset).

  From Acceptance Tests/UC-21-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-21-AT.md#L84) AT-21-08:

  > Then the system applies precedence rules (preferred source, highest quality,
  > most recent)

  Why this is ambiguous

  The sources require precedence rules, but they do not define which criterion
  wins when source attributes conflict. That changes canonical-entity
  construction and can produce different canonical names, coordinates, or
  categories for the same inputs.

  Recommended: Option A - preferred source first, then highest quality, then
  most recent. This gives the maintainer a stable, governance-friendly primary
  authority while still using quality and recency as deterministic tie-breakers.

  | Option | Description |
  |--------|-------------|
  | A | Prefer the configured preferred source first, then highest quality, then
  most recent update. |
  | B | Prefer the highest-quality source first, then most recent update, then
  preferred source as tie-breaker. |
  | C | Prefer the most recent update first, then highest quality, then
  preferred source. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


UC-22:
No critical ambiguities detected worth formal clarification.


UC-23:

## Question 1: Validation Failure Status Code

  Context

  From UC-23.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-23.md), Extensions, 7a:

  > 7a: Request payload fails validation (missing fields, malformed geo-shape,
  > invalid address structure)
  > 7a1: Estimate API returns HTTP 400 with structured field-level errors and
  > suggestions.

  From UC-23-AT.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Acceptance%20Tests/UC-23-AT.md), AT-UC23-005 — Validation Error: Malformed
  Polygon:

  > Expected Results:
  >
  > - System returns HTTP 422.

  Why this is ambiguous

  The use case says validation failures return HTTP 400, while the acceptance
  test for malformed polygon expects HTTP 422. That changes implementation
  behavior, response-contract tests, and how the spec should state validation
  requirements.

  Recommended: Option B - Use 400 for generic payload validation and 422 for
  semantically invalid but well-formed geo-shapes. This preserves both source
  statements with the least contradiction and gives a stable rule for tests.

  | Option | Description |
  |--------|-------------|
  | A | Use HTTP 400 for all request validation failures, including malformed
  polygons. |
  | B | Use HTTP 400 for generic payload validation errors and HTTP 422 for
  semantically invalid but well-formed inputs like self-intersecting polygons. |
  | C | Use HTTP 422 for all validation failures described in 7a, and treat the
  UC’s 400 as outdated. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


UC-24:
## Question 1: Out-of-coverage map behavior

  Source quote
  Use Cases/UC-24.md → ## Extensions

  > -   **10a2**: Map optionally pans to nearest supported boundary region.

  Acceptance Tests/UC-24-AT.md → ### AT-UC24-008 — Out-of-Coverage Address
  Handling

  > - Map behavior follows spec (no change or boundary pan).

  Why this is ambiguous
  The current sources require a coverage warning, but they leave the actual map
  behavior open between two different outcomes. That changes implementation, UI
  behavior, and the expected assertion in AT-UC24-008.

  Recommended: Option A - Keep the map unchanged. It is the lower-risk behavior,
  avoids implying support for an unsupported location, and matches the failed-
  end-condition pattern already used elsewhere in UC-24.

  | Option | Description |
  |--------|-------------|
  | A | Keep the current map view unchanged after showing the out-of-coverage
  warning. |
  | B | Pan the map to the nearest supported boundary region after showing the
  warning. |
  | C | Pan only when boundary geometry is available; otherwise keep the map
  unchanged. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


UC-25:
No critical ambiguities detected worth formal clarification.


UC-26:
## Question 1: Standard partial-data warning presentation

  Context:

  From ./Use Cases/UC-26.md (./Use%20Cases/UC-26.md), ## Main Success Scenario:

  > 7. **UI** displays a warning panel listing missing factors

  From ./Acceptance Tests/UC-26-AT.md (./Acceptance%20Tests/UC-26-AT.md), ###
  AT-UC26-002 — Warning for Missing Optional Dataset:

  > - Yellow warning banner appears with message:
  > "Partial Data: Crime statistics temporarily unavailable. Estimate uses
  > incomplete data."

  This is ambiguous because a normal partial-data case could be implemented as a
  panel, a banner, or both. That changes the UI structure, component behavior,
  and what the acceptance test should verify.

  Recommended: Option C - show a warning panel that includes a banner-style
  header. It preserves the use-case requirement for a panel while satisfying the
  acceptance test’s visible yellow banner/message expectation.

  | Option | Description |
  |--------|-------------|
  | A | Standard partial-data warnings use a banner only, with no expandable
  panel unless severity is very low. |
  | B | Standard partial-data warnings use a panel only; the acceptance test
  banner wording is treated as non-normative example text. |
  | C | Standard partial-data warnings use a warning panel with a banner-style
  header/message, so both sources are satisfied together. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› c


• ## Question 2: Confidence indicator format

  Context:

  From ./Use Cases/UC-26.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Use%20Cases/UC-26.md), ## Main Success Scenario:

  > 6. **UI** displays a confidence indicator (e.g., high/medium/low).

  From ./Acceptance Tests/UC-26-AT.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Acceptance%20Tests/UC-26-AT.md), ### AT-UC26-002 —
  Warning for Missing Optional Dataset:

  > - Confidence indicator shows 78% (reduced from normal 85%)

  This is ambiguous because the UI could show only a qualitative label, only a
  percentage, or both. That changes rendering, data mapping, and test
  assertions.

  Recommended: Option C - show both a percentage and a qualitative label when
  available. It satisfies the acceptance test’s numeric check while preserving
  the use case’s high/medium/low style.

  | Option | Description |
  |--------|-------------|
  | A | Show qualitative confidence only, such as High, Medium, or Low. |
  | B | Show percentage confidence only, such as 78%. |
  | C | Show both percentage and qualitative label, such as 78% and Medium. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› c


UC-27:
## Question 1: Handling unreasonable straight-line fallback values

  Context:

  From UC-27.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-27.md), ## Extensions:

  > -   **7a**: Straight-line approximation produces unreasonable value
  >     (e.g., ocean crossing)
  >     -   **7a1**: Distance Service caps maximum fallback distance.
  >     -   **7a2**: Factor is excluded and marked as unreliable.

  From UC-27-Scenarios.md (/home/fronk/ECE493/Capstone/Group/
  ece493_2026w_group14/Scenarios/UC-27-Scenarios.md), ## Alternative Path 7a --
  Unreasonable Straight-Line Distance:

  > The Distance Service applies a reasonableness check.
  > The straight-line distance of 0.45 km through water is multiplied by a
  > configurable correction factor of 3.5x...
  > Alternatively, if the correction factor results in an unreasonable
  > adjustment ..., the Distance Service may completely exclude the factor and
  > mark it as unreliable.

  This is ambiguous because implementation could always cap/adjust, always
  exclude, or do one then the other conditionally. That changes fallback logic,
  returned distance values, and how downstream valuation uses the factor.

  Recommended: Option C - cap or adjust first, then exclude only if the result
  is still unreasonable. It preserves both UC-27 extension steps, reduces
  unnecessary data loss, and gives the valuation engine a deterministic
  escalation path.

  | Option | Description |
  |--------|-------------|
  | A | Always cap or adjust unreasonable straight-line values and keep the
  factor. |
  | B | Always exclude the factor and mark it unreliable whenever the straight-
  line value is unreasonable. |
  | C | Apply capping or adjustment first; if the result is still unreasonable,
  exclude the factor and mark it unreliable. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› c


• ## Question 2: Error status when fallback is disabled

  Context:

  From UC-27.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-27.md), ## Extensions:

  > -   **6a**: Straight-line fallback disabled by configuration
  >     -   **6a2**: Estimate API returns HTTP 503 or 424 indicating routing
  > dependency unavailable.

  From UC-27-AT.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Acceptance%20Tests/UC-27-AT.md), ### AT-UC27-004 — Fallback Disabled Causes
  Error:

  > - Controlled error returned (503/424).

  This is ambiguous because the implementation and tests need to know whether
  one status code is canonical, whether both are acceptable, or whether they
  depend on request mode. That affects API contract and acceptance assertions.

  Recommended: Option A - use 503 as the canonical status. It is the safer
  default for an unavailable external dependency and avoids splitting client/
  test handling across two status codes.

  | Option | Description |
  |--------|-------------|
  | A | Always return HTTP 503 when fallback is disabled and routing fails. |
  | B | Always return HTTP 424 when fallback is disabled and routing fails. |
  | C | Allow either 503 or 424 depending on request context or configuration. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


• ## Question 3: Error status for invalid property coordinates

  Context:

  From UC-27.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-27.md), ## Extensions:

  > -   **5a**: Property coordinates are missing or invalid
  >     -   **5a2**: Estimate API returns error HTTP 422 indicating invalid
  > location reference.

  From UC-27-AT.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Acceptance%20Tests/UC-27-AT.md), ### AT-UC27-005 — Missing Coordinates Prevent
  Fallback:

  > - Validation error 400/422.

  This is ambiguous because the use case names 422, while the acceptance test
  allows 400/422. Picking one canonical status affects the API contract and what
  the acceptance test should assert.

  Recommended: Option B - use 422 as the canonical status. It matches the use
  case directly and cleanly distinguishes invalid coordinate content from a
  generic malformed request.

  | Option | Description |
  |--------|-------------|
  | A | Always return HTTP 400 for invalid or missing property coordinates. |
  | B | Always return HTTP 422 for invalid or missing property coordinates. |
  | C | Allow either 400 or 422 depending on the validation failure details. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


UC-28:
## Question 1: Response status when too many factors are missing

  Context:

  From UC-28.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-28.md), ## Extensions:

  > -   **6a**: Too many factors missing (below minimum threshold)
  >     -   **6a2**: Estimate API may return HTTP 206 Partial Content or
  >         HTTP 200 with warning severity HIGH.

  From UC-28-AT.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Acceptance%20Tests/UC-28-AT.md), ### AT-UC28-003 — Too Many Missing Factors
  Handling:

  > - Response indicates low reliability (200+warning or 206).

  This is ambiguous because the API contract and tests need to know whether low-
  reliability partial estimates use a success response with warnings or a
  partial-content response. That choice changes client handling, status-code
  assertions, and downstream error semantics.

  Recommended: Option A - always return HTTP 200 with a high-severity warning
  for low-reliability partial estimates. It preserves the “usable estimate” goal
  of UC-28 while keeping low reliability as result metadata rather than
  transport-level partial-content semantics.

  | Option | Description |
  |--------|-------------|
  | A | Always return HTTP 200 with a high-severity warning when the estimate is
  low reliability but still returned. |
  | B | Always return HTTP 206 Partial Content when the estimate is low
  reliability due to too many missing factors. |
  | C | Return HTTP 200 or 206 depending on completeness threshold bands or
  configuration. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a



• ## Question 2: Error status when baseline assessment is missing

  Context:

  From UC-28.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-28.md), ## Extensions:

  > -   **5a**: Critical dataset missing (baseline assessment value missing)
  >     -   **5a2**: API returns HTTP 424/422 indicating baseline is
  >         required.

  From UC-28-AT.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Acceptance%20Tests/UC-28-AT.md), ### AT-UC28-004 — Baseline Missing Fails:

  > - HTTP 422/424 returned.
  > - Error indicates baseline required.

  This is ambiguous because the API and tests need one canonical status for a
  missing baseline dependency. Choosing 422 versus 424 changes client behavior
  and how the failure is categorized.

  Recommended: Option B - always return HTTP 424. The baseline is described as a
  critical prerequisite dependency rather than malformed user input, and the
  scenario narrative for UC-28 also uses 424 Failed Dependency.

  | Option | Description |
  |--------|-------------|
  | A | Always return HTTP 422 when baseline assessment is missing. |
  | B | Always return HTTP 424 when baseline assessment is missing. |
  | C | Return 422 or 424 depending on why the baseline is unavailable. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


• ## Question 3: Strict mode support in this feature

  Context:

  From UC-28.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-28.md), ## Extensions:

  > -   **7a**: User requested strict mode (must include certain factors)
  >     -   **7a1**: Estimate API returns HTTP 424 indicating requested
  >         factor unavailable.
  >     -   **7a2**: Response lists missing required datasets.

  From UC-28-AT.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Acceptance%20Tests/UC-28-AT.md), ### AT-UC28-006 — Strict Mode Requires
  Factors (If Supported):

  > **Preconditions:**
  > - Strict mode supported

  This is ambiguous because the use case includes strict mode as an extension,
  while the acceptance test makes it conditional with “If Supported.” That
  changes whether strict mode is part of the required scope for this feature or
  left optional for later work.

  Recommended: Option A - treat strict mode as in scope and supported for UC-28.
  It is explicitly present in the use case flow, and making it optional would
  weaken traceability between the use case and the spec.

  | Option | Description |
  |--------|-------------|
  | A | Strict mode is supported and in scope for this feature. |
  | B | Strict mode is out of scope for this feature and should be deferred. |
  | C | Strict mode is optional and implementation-dependent. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a

UC-29:
## Question 1: Cache Scope

  Context
  Source: UC-29.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-29.md)
  Section: Goal in Context

  > "The backend system caches frequently requested computations (full estimates
  > and/or expensive feature computations like distance queries) to reduce
  > latency and cost for repeated requests."

  Section: Related Information / Open Issues

  > "Decide whether to cache full estimates, intermediate features, or both."

  This is a real implementation ambiguity because it changes what gets cached,
  what cache keys represent, which invalidation rules apply, and whether the
  feature includes only estimate-level caching or also sub-computation caching.
  It would also change what work is planned beyond the current acceptance tests.

  Recommended: Option A - cache full estimates only. The main flow and all
  acceptance tests are written around estimate-level cache hits, misses,
  staleness, and corruption; choosing this keeps the spec congruent with the
  current source-of-truth behavior and avoids adding unsupported scope.

  | Option | Description |
  |--------|-------------|
  | A | Cache full estimates only for this feature. |
  | B | Cache intermediate expensive feature computations only. |
  | C | Cache both full estimates and intermediate computations. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› a


UC-30:
No critical ambiguities detected worth formal clarification.


UC-31:
## Question 1: Open-Data Freshness in Health Checks

  Context
  Source: UC-31.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-31.md)
  Section: Main Success Scenario

  > "open-data feature sources (optional check)."

  Section: Related Information / Open Issues

  > "Decide whether health check should verify freshness of open-data
  > ingestion."

  This is a real implementation ambiguity because it changes what /health
  checks, what dependency status can become degraded or unhealthy, and whether
  stale ingestion data appears in health responses and alerts. It does not
  appear resolved in the acceptance tests.

  Recommended: Option B - include open-data freshness as a degraded-only check.
  That gives operational visibility into stale ingestion without making the core
  service appear fully unavailable when primary runtime dependencies are still
  up.

  | Option | Description |
  |--------|-------------|
  | A | Do not check open-data freshness in /health; only connectivity is
  reported. |
  | B | Check open-data freshness in /health, and report stale ingestion as
  Degraded. |
  | C | Check open-data freshness in /health, and treat stale ingestion as
  Unhealthy. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b


UC-32:
## Question 1: Correction Guidance Format

  Context
  Source: UC-32.md (/home/fronk/ECE493/Capstone/Group/ece493_2026w_group14/
  Use%20Cases/UC-32.md)
  Section: Main Success Scenario

  > "Estimate API constructs an error response containing:"
  > "- recommended correction example."

  Section: Related Information / Open Issues

  > "Decide whether to include example corrected payload in error response."

  This is a real implementation ambiguity because it changes the shape and size
  of the error response. A short field-level hint, a full corrected payload
  example, or no payload example at all lead to different response schemas and
  different client expectations.

  Recommended: Option B - include field-level correction examples, but not a
  full corrected payload. That satisfies the use case requirement for actionable
  correction guidance while minimizing response bloat and reducing the risk of
  echoing sensitive input structure back to the client.

  | Option | Description |
  |--------|-------------|
  | A | Include a full corrected payload example in the error response. |
  | B | Include only field-level correction examples or hints, not a full
  payload. |
  | C | Do not include correction examples; include only error reasons. |
  | Short | Provide a different short answer (<=5 words). |

  You can reply with the option letter (e.g., "A"), accept the recommendation by
  saying "yes" or "recommended", or provide your own short answer.


› b

