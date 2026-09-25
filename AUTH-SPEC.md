# RuleForge Authentication & Authorization Specification (V4.3.0)

This document defines the security contract for accessing the RuleForge API.
The Core Engine remains completely unaware of authentication, authorization, HTTP, or users. Security is enforced strictly at the FastAPI transport layer.

## 1. Philosophy
- **Auth-Agnostic Core:** The RuleForge Core and Repository layers have no knowledge of API Keys, JWTs, or Scopes.
- **Dependency Injection:** FastAPI Dependencies intercept requests, validate credentials, and enforce scopes before reaching the business logic.
- **No Secret Leakage:** Plaintext API keys are NEVER stored in the database. Credentials must NEVER appear in logs or error messages.

## 2. Scopes
Authorization is based on a strict scope system:
- `rules:read`: GET rules.
- `rules:write`: POST rules.
- `rules:activate`: POST activate endpoints.
- `rules:evaluate`: POST evaluate endpoints.
- `rules:admin`: DELETE (archive) rules.

## 3. Endpoint Protection Matrix
| Endpoint | Method | Required Scope |
| :--- | :--- | :--- |
| `/v1/rules` | GET | `rules:read` |
| `/v1/rules/{id}` | GET | `rules:read` |
| `/v1/rules` | POST | `rules:write` |
| `/v1/rules/{id}/versions/{v}/activate` | POST | `rules:activate` |
| `/v1/rules/{id}` | DELETE | `rules:admin` |
| `/v1/rules/{id}/evaluate` | POST | `rules:evaluate` |
| `/v1/evaluate` | POST | `rules:evaluate` |

## 4. API Keys
For machine-to-machine integration (e.g., Vantari, ContaFlow).

### 4.1. Database Model (`api_keys` table)
- `id` (UUID): Primary key.
- `key_hash` (String): SHA-256 hash of the API key.
- `name` (String): Human-readable identifier (e.g., "ContaFlow Production").
- `status` (Enum): `ACTIVE`, `REVOKED`.
- `scopes` (JSON/Array): List of allowed scopes.
- `created_at` (DateTime)
- `last_used_at` (DateTime, nullable)
- `expires_at` (DateTime, nullable)

### 4.2. Key Lifecycle
- When an API key is created, a random secure string is generated.
- It is hashed, and ONLY the hash is saved to the database.
- The plaintext key is returned to the user EXACTLY ONCE.
- Verification compares the hash of the incoming key with the database hash.

## 5. Security Test Matrix (AUTH-001 to AUTH-018)
The following guarantees must be covered by automated tests:
- AUTH-001: Unauthenticated request rejected (401).
- AUTH-002: Valid API key accepted (200).
- AUTH-003: Invalid API key rejected (401).
- AUTH-004: Revoked API key rejected (401).
- AUTH-005: Expired API key rejected (401).
- AUTH-006: Missing scope rejected (403).
- AUTH-007: `rules:read` accepted for GET.
- AUTH-008: `rules:write` accepted for POST.
- AUTH-009: `rules:activate` accepted.
- AUTH-010: `rules:evaluate` accepted.
- AUTH-011: Admin endpoint protected.
- AUTH-012: Valid JWT accepted (Future V4.3.x).
- AUTH-013: Invalid JWT rejected.
- AUTH-014: Expired JWT rejected.
- AUTH-015: JWT insufficient scope rejected (403).
- AUTH-016: API key hash never returned in any response.
- AUTH-017: Credentials never appear in logs.
- AUTH-018: Authentication logic does not reach the Core Engine.
