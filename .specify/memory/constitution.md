<!--
Sync Impact Report
- Version change: N/A (template) → 0.1.0
- Modified principles: None (initial adoption)
- Added sections: Core Principles (filled), Project Constraints & Sources, Development Workflow & Quality Gates
- Removed sections: None
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md
  - ✅ .specify/templates/spec-template.md
  - ✅ .specify/templates/tasks-template.md
  - ⚠ .specify/templates/commands/*.md (directory not found in repo)
  - ✅ README.md (reviewed; no updates required)
- Follow-up TODOs:
  - TODO(RATIFICATION_DATE): original adoption date not found in repo
-->
# Property Value Estimator Constitution

## Core Principles

### Code Quality First
All production code MUST be linted and formatted, free of dead code, and structured
into clear modules (no oversized files). Public Python functions MUST include type
hints; public JavaScript functions MUST have explicit parameter expectations in
docstrings or inline comments where types are ambiguous. Complexity hotspots MUST be
refactored or justified in the PR description.

### Testing Standards (NON-NEGOTIABLE)
Every use case MUST have acceptance tests traceable to `Acceptance Tests/UC-XX-AT.md`.
Changes to valuation logic or data processing MUST include automated unit tests.
API or integration boundaries MUST have integration tests covering happy path and
failure modes. Tests MUST pass before merge and failures block release.

### UX Consistency
User-facing flows MUST use consistent labels, validation rules, and interaction
patterns across screens. Shared UI styles and components MUST be reused; deviations
require a documented rationale and a matching update to the shared styles. All new
UI changes MUST include a basic accessibility pass (keyboard navigation and contrast).

### Performance Requirements
The app MUST remain responsive: interactive UI updates within 100 ms for local
state changes, and estimate requests MUST meet p95 < 1.5 s with cached data and
p95 < 3.5 s when cache misses require computation. Performance regressions MUST be
measured and resolved or explicitly accepted in the PR description.

## Project Constraints & Sources

- **Stack**: Vanilla HTML, CSS, JavaScript, and Python only.
- **Use cases**: `Use Cases/UC-XX.md`
- **Scenarios**: `Scenarios/UC-XX-Scenarios.md`
- **Acceptance tests**: `Acceptance Tests/UC-XX-AT.md`
- New or updated use cases MUST update the corresponding scenario and acceptance
  test files.

## Development Workflow & Quality Gates

- All work MUST map to a use case ID (UC-XX) and reference the related scenario
  and acceptance test files.
- Code review is required for all merges.
- Required gates before merge: lint/format clean, automated tests passing,
  UX consistency check completed, and performance budgets verified or waivered
  with explicit rationale.

## Governance

- This constitution supersedes all other development practices.
- Amendments require documentation in the PR, an impact note, and a version bump.
- Versioning follows semantic versioning:
  - MAJOR: backward-incompatible governance/principle changes
  - MINOR: new principle or materially expanded guidance
  - PATCH: clarification or non-semantic edits
- Compliance review MUST occur in every spec/plan/tasks review using a
  Constitution Check section.

**Version**: 0.1.0 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date unknown | **Last Amended**: 2026-03-09
