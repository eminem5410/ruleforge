# RuleForge Observability Specification (V5.0.0)

This document defines the observability contract for the RuleForge API.
Observability is strictly enforced at the FastAPI transport layer. The Core Engine remains completely free of logging, metrics, or tracing dependencies.

## 1. Philosophy
- **Transport Concern:** Logging, Metrics, and Tracing are handled by FastAPI middleware and dependencies.
- **Zero Core Footprint:** The `ruleforge/lexer`, `ruleforge/parser`, `ruleforge/semantic`, and `ruleforge/evaluator` modules MUST NOT import observability libraries.
- **Security Redaction:** Sensitive data (API keys, context data, medical/financial info) MUST NEVER appear in logs or traces.

## 2. Structured Logging
All application logs must be output in JSON format to stdout for log aggregation (ELK, Datadog, etc.).

### Log Structure Example
{
  "timestamp": "2026-09-25T15:30:12.431Z",
  "level": "INFO",
  "logger": "ruleforge.api",
  "event": "rule_evaluation",
  "rule_id": "vip_check",
  "rule_version": 1,
  "duration_ms": 1.42,
  "success": true,
  "request_id": "req_12345"
}

## 3. Prometheus Metrics
Metrics will be exposed at `/metrics` using `prometheus_client`.

### Base Metrics
- `ruleforge_requests_total` (Counter): Total HTTP requests, labeled by `method`, `endpoint`, `status`.
- `ruleforge_request_duration_seconds` (Histogram): HTTP request latency.
- `ruleforge_evaluations_total` (Counter): Total rule evaluations, labeled by `success`.
- `ruleforge_evaluation_duration_seconds` (Histogram): Time spent inside the RuleForge Engine.
- `ruleforge_registry_operations_total` (Counter): Registry DB operations, labeled by `operation`, `success`.

### Cardinality Rule
High-cardinality data (like `rule_id`, `tenant_id`, or context values) MUST NOT be used as Prometheus labels.

## 4. OpenTelemetry Tracing
Distributed tracing will be implemented via OpenTelemetry (OTel) instrumentation.

### Initial Spans (V5.0.0)
- Root Span: HTTP Request
- Child Span 1: Authentication
- Child Span 2: Registry Lookup (if applicable)
- Child Span 3: RuleForge Evaluation

### Internal Spans (V5.1.0+)
Later versions may introduce deeper spans for `lexer`, `parser`, and `evaluator`, but V5.0.0 focuses on the high-level flow to avoid telemetry overhead.
