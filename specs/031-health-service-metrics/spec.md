# Feature Specification: Provide Health Checks and Service Metrics

**Feature Branch**: `031-health-service-metrics`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-31.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-31-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-31-AT.md"

## Clarifications

### Session 2026-03-10

- Q: Should `/health` verify open-data ingestion freshness, and how should stale ingestion be classified? → A: Check open-data freshness in `/health` and report stale ingestion as Degraded.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Monitor Overall Service Health (Priority: P1)

As a maintainer or monitoring system, I want to call the health endpoint and receive an accurate service status with dependency breakdown so that outages and degraded operating conditions can be detected quickly.

**Why this priority**: Health reporting is the primary operational capability because it determines whether outages in critical dependencies can be detected and escalated.

**Independent Test**: Can be fully tested by calling the health endpoint with all dependencies up, with a non-critical dependency down, and with a critical dependency down, then verifying the returned status and dependency reporting.

**Acceptance Scenarios**:

1. **Given** all dependencies are operational, **When** `GET /health` is called, **Then** the response returns HTTP 200 with Healthy status and dependency checks marked OK.
2. **Given** the routing provider is down and fallback exists, **When** `GET /health` is called, **Then** the response returns Degraded status with routing-provider impact information while the service remains operational.
3. **Given** the feature store is down, **When** `GET /health` is called, **Then** the response returns Unhealthy status and indicates feature store failure.

---

### User Story 2 - Expose Operational Metrics Safely (Priority: P2)

As a maintainer or monitoring system, I want the metrics endpoint to expose operational counters and latency information without exposing sensitive values so that dashboards and alerts can be powered safely.

**Why this priority**: Metrics exposure is necessary for dashboards, alerting, and trend analysis, but it must avoid leaking raw property or user information.

**Independent Test**: Can be fully tested by generating representative traffic, requesting the metrics endpoint, and verifying required aggregate metrics are present while raw identifiers and PII are absent.

**Acceptance Scenarios**:

1. **Given** metrics are enabled and representative traffic has been generated, **When** `GET /metrics` is called, **Then** request counts, error counts, latency metrics, and implemented domain metrics are present.
2. **Given** metrics output is inspected for sensitive data, **When** the monitoring system scans for raw addresses or identifiers, **Then** only aggregated labels are exposed and no raw PII is present.

---

### User Story 3 - Protect Monitoring Endpoints and Alert on Failures (Priority: P3)

As a maintainer or monitoring system, I want monitoring endpoints to remain usable under dependency failures and excessive polling so that health and metrics collection do not destabilize the service.

**Why this priority**: The monitoring path must stay trustworthy and protected even during outages or abusive request patterns.

**Independent Test**: Can be fully tested by simulating metrics-storage failure and excessive health polling, then confirming health reporting continues, failures are logged, and excess polling is rate limited.

**Acceptance Scenarios**:

1. **Given** the metrics storage system is unreachable, **When** health and metrics reporting continue, **Then** health is still reported and metrics export failure is logged for the maintainer.
2. **Given** health polling exceeds the configured limit, **When** requests burst beyond the limit, **Then** excess requests are rate limited and the service remains stable.

### Edge Cases

- If the feature store database is down, health status must be marked Unhealthy and monitoring must trigger a high-severity alert.
- If the routing provider is down and a straight-line fallback exists, health status must be marked Degraded and metrics must include increased fallback usage.
- If the metrics storage system is unreachable, the service must still report health while logging the metrics export failure and alerting the maintainer via logs.
- If metrics contain sensitive values, the system must redact property identifiers or user data and expose only aggregated metrics.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-01-001**: The system MUST allow the monitoring system to request the `/health` endpoint.
- **FR-01-002**: The system MUST check internal service status, including API running state, thread pool status, and memory usage, when servicing a health request.
- **FR-01-003**: The system MUST check connectivity to critical dependencies, including the Feature Store database, cache service, routing provider, valuation engine, and optional open-data feature sources, when servicing a health request.
- **FR-01-003A**: When open-data feature sources are included in health checks, the system MUST verify open-data ingestion freshness and classify stale ingestion as Degraded.
- **FR-01-004**: The system MUST assign a health status level of Healthy, Degraded, or Unhealthy based on dependency reachability.
- **FR-01-005**: The system MUST return a health response that includes the overall status and dependency statuses.
- **FR-01-006**: The system MUST allow the monitoring system to record health status and trigger an alert when the service is unhealthy.
- **FR-01-007**: The system MUST allow the monitoring system to request the `/metrics` endpoint.
- **FR-01-008**: The system MUST return operational metrics including request count, error rate, cache hit ratio, routing fallback usage, average latency, and valuation engine processing time.
- **FR-01-009**: The system MUST allow the monitoring system to store returned metrics for dashboard visualization and alerting.
- **FR-01-010**: The system MUST mark health status as Unhealthy when the Feature Store database is down and support triggering a high-severity alert.
- **FR-01-011**: The system MUST mark health status as Degraded when the routing provider is down and a straight-line fallback exists, and MUST include increased fallback usage in metrics.
- **FR-01-012**: The system MUST continue reporting health when the metrics storage system is unreachable and MUST log the metrics export failure so the maintainer can be alerted via logs.
- **FR-01-013**: The system MUST support rate limiting of health endpoint requests when excessive polling occurs.
- **FR-01-014**: The system MUST redact property identifiers and user data from metrics output when sensitive values would otherwise be exposed.
- **FR-01-015**: The system MUST expose only aggregated metrics output.

### Non-Functional Requirements

- **NFR-001**: Health and metrics endpoints MUST provide accurate operational information for monitoring and alerting.
- **NFR-002**: Monitoring endpoints MUST remain stable under excessive polling and partial dependency failure.
- **NFR-003**: Delivery of this feature MUST remain within the project implementation constraints of Python and vanilla HTML/CSS/JS.

### Key Entities *(include if feature involves data)*

- **Health Response**: The returned service-health result containing overall status and dependency statuses.
- **Dependency Status**: The status information for each checked dependency or internal subsystem.
- **Metrics Output**: The exposed aggregated operational statistics used for dashboards and alerting.
- **Monitoring Alert**: The alert generated when unhealthy or degraded conditions require maintainer attention.
- **Polling Request**: A monitoring-system request to the health or metrics endpoints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of health requests return a status classification and dependency breakdown that match the current dependency state in tested healthy, degraded, and unhealthy scenarios.
- **SC-002**: 100% of metrics responses include request and error counts plus latency information when metrics are enabled.
- **SC-003**: 100% of metrics outputs omit raw property identifiers and raw user data.
- **SC-004**: Under excessive health polling, excess requests are rate limited without causing service instability.

## Summary / Goal

The goal of this feature is to expose health and metrics endpoints that allow maintainers to detect outages, observe service behavior, and alert safely on degraded or unhealthy conditions.

For this feature, `/health` includes open-data ingestion freshness checks and reports stale ingestion as Degraded.

## Actors

- Primary actor: Maintainer / Monitoring System
- Secondary actors: Metrics Collector; Alerting System; API Gateway; Feature Store; Routing Provider; Valuation Engine

## Preconditions

- Health endpoints are implemented and deployed.
- Metrics collection system is configured.
- Monitoring system has permission to access the endpoints.

## Triggers

- Monitoring system polls health endpoints or metrics endpoints.

## Main Flow

1. **Monitoring System** sends request to `/health` endpoint.
2. **Backend Service** checks internal service status (API running, thread pool, memory usage).
3. **Backend Service** checks connectivity to critical dependencies:
   - Feature Store database,
   - Cache service,
   - Routing provider,
   - Valuation engine,
   - open-data feature sources (optional check).
4. **Backend Service** assigns a status level:
   - Healthy (all dependencies reachable),
   - Degraded (non-critical dependency down),
   - Unhealthy (critical dependency down).
5. **Backend Service** returns health response including dependency statuses.
6. **Monitoring System** records status and triggers alert if unhealthy.
7. **Monitoring System** requests `/metrics` endpoint.
8. **Backend Service** returns metrics such as:
   - request count,
   - error rate,
   - cache hit ratio,
   - routing fallback usage,
   - average latency,
   - valuation engine processing time.
9. **Monitoring System** stores metrics for dashboard visualization and alerting.
10. **Maintainer** reviews dashboards and responds to alerts as needed.

## Alternate Flows

### 3b: Routing provider is down

- **3b1**: Health status marked Degraded (if straight-line fallback exists).
- **3b2**: Metrics include increased fallback usage.

### 3c: Metrics storage system is unreachable

- **3c1**: Service still reports health but logs metrics export failure.
- **3c2**: Maintainer alerted via logs.

### 5a: Health endpoint is attacked with excessive polling

- **5a1**: API gateway rate limits requests.
- **5a2**: Monitoring uses configured polling frequency.

### 8a: Metrics contain sensitive values

- **8a1**: System redacts property identifiers or user data from metrics output.
- **8a2**: Only aggregated metrics are exposed.

## Exception / Error Flows

### 3a: Feature Store database is down

- **3a1**: Health status marked Unhealthy.
- **3a2**: Monitoring triggers high-severity alert.

## Data Involved

- Internal service status
- Thread pool status
- Memory usage
- Dependency statuses
- Feature Store database connectivity
- Cache service connectivity
- Routing provider connectivity
- Valuation engine connectivity
- Open-data feature source connectivity
- Health response status level
- Request count
- Error rate
- Cache hit ratio
- Routing fallback usage
- Average latency
- Valuation engine processing time
- Metrics output
- Alert status

## Traceability

### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
|---|---|
| AT-UC31-001 — Health Healthy | FR-01-001, FR-01-002, FR-01-003, FR-01-004, FR-01-005 |
| AT-UC31-002 — Health Degraded on Routing Down | FR-01-003, FR-01-004, FR-01-005, FR-01-011 |
| AT-UC31-003 — Health Unhealthy on Feature Store Down | FR-01-003, FR-01-004, FR-01-005, FR-01-010 |
| AT-UC31-004 — Metrics Expose Core Counters | FR-01-007, FR-01-008, FR-01-009 |
| AT-UC31-005 — Metrics Redaction | FR-01-014, FR-01-015 |
| AT-UC31-006 — Health Rate Limited | FR-01-013 |

### Flow Steps / Sections to Functional Requirements

| Flow Step or Section | Related FRs |
|---|---|
| Main Flow 1 | FR-01-001 |
| Main Flow 2 | FR-01-002 |
| Main Flow 3 | FR-01-003, FR-01-010, FR-01-011, FR-01-012 |
| Main Flow 4 | FR-01-004 |
| Main Flow 5 | FR-01-005 |
| Main Flow 6 | FR-01-006 |
| Main Flow 7 | FR-01-007 |
| Main Flow 8 | FR-01-008, FR-01-014, FR-01-015 |
| Main Flow 9 | FR-01-009 |
| Alternate Flow 3b | FR-01-011 |
| Alternate Flow 3c | FR-01-012 |
| Alternate Flow 5a | FR-01-013 |
| Alternate Flow 8a | FR-01-014, FR-01-015 |
| Exception Flow 3a | FR-01-010 |

## Assumptions

- The acceptance test expectation for core metrics is interpreted as requiring request and error counts plus latency metrics, with cache-hit and fallback metrics included where the feature exposes them as described by the use case.
- The scenario narrative was not needed to derive requirements because the use case flow and acceptance tests were sufficient.
- The use case open issue on open-data freshness is resolved for this feature by checking freshness in `/health` and treating stale ingestion as a Degraded condition.
