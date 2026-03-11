# Research: Standardize POI categories across sources

**Date**: 2026-03-11
**Spec**: `specs/020-standardize-poi-categories/spec.md`

## Goals

- Define mapping and governance rules for standardizing POI categories.
- Clarify conflict detection and unmapped thresholds.
- Ensure deterministic reclassification using stored raw categories.

## Findings

- Conflicts always block promotion regardless of permissive unmapped governance.
- Unmapped labels can be promoted with warnings only when governance allows.
- Precedence rules are required when multiple source category fields exist.
- Taxonomy changes must trigger reclassification without re-ingesting POIs.

## Open Questions

- What are the configured thresholds for unmapped rates and conflict rates?
- What identifiers represent taxonomy and mapping versions?
- How are mapping rules stored (table vs config file)?

## Decisions (initial)

- Store raw category fields and mapping rule identifiers in standardized outputs.
- Record conflict details by source and raw label.
- Use atomic promotion for standardized outputs.
