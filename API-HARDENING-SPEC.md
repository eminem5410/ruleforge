# RuleForge API Hardening Specification (V3.2.0)

This document defines the hardening rules for the RuleForge REST API to ensure it is predictable, safe, and does not leak internal implementation details.

## 1. Dynamic Versioning
The API metadata (FastAPI title/version) must be dynamically read from the installed package metadata (importlib.metadata) to avoid hardcoding mismatches with pyproject.toml or Docker images.

## 2. Internal Error Sanitization
Unhandled exceptions (500 Internal Server Error) must NOT return internal Python tracebacks or exception messages to the client.
Response should strictly be:
{"error": {"code": "INTERNAL", "message": "Internal server error"}}
Detailed error messages must be logged server-side.

## 3. Immutable Request Normalization
The API must not mutate the incoming request DTO during type normalization.
`normalize_context` must operate on a deep copy of the original `request.context` to prevent side effects.

## 4. Schema Type Validation
The API must validate the `context_schema` before passing it to the Core.
Allowed types: Integer, Decimal, String, Boolean, Date.
Any unknown type in the schema must result in a 422 Unprocessable Entity.

## 5. Structural Validation
Explicit tests must ensure that passing invalid JSON structures (e.g., lists instead of objects for `context` or `context_schema`) are safely rejected by Pydantic.

## 6. Test Coverage Matrix (API-001 to API-013)
The following scenarios must be covered by automated tests:
API-001: Health check
API-002: Valid evaluation
API-003: Semantic error (RF3xxx -> 400)
API-004: Missing required field (-> 422)
API-005: Decimal serialization (string to Decimal)
API-006: Explain mode (trace generation)
API-007: Invalid Decimal format (RF4003 -> 400)
API-008: Invalid context structure (list instead of dict -> 422)
API-009: Invalid schema type (e.g., "Float" instead of "Decimal" -> 422)
API-010: Invalid schema structure (list instead of dict -> 422)
API-011: Internal error sanitization (no stacktrace leakage)
API-012: NULL handling in context
API-013: Date serialization (ISO string to Date)
