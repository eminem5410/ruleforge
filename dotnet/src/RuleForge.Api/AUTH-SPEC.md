# RuleForge.NET API Security Specification (V6.1.0)

This document defines the security contract for the RuleForge ASP.NET Core API.
Security is enforced strictly at the HTTP layer using ASP.NET Core Middleware and Authorization Policies.
The `RuleForge.Core` engine remains completely unaware of authentication or authorization.

## 1. Authentication
- **Scheme:** Bearer Token.
- **Header:** `Authorization: Bearer <api_key>`
- **Implementation:** Custom ASP.NET Core Middleware (`ApiKeyMiddleware`) that intercepts requests, validates the token, and injects the `ApiKey` context.

## 2. Authorization (Scopes)
Authorization is based on a strict scope system attached to the API Key.
- `rules:evaluate`: Required to call `POST /api/v1/evaluate`.
- `rules:read`: Required to call `GET` endpoints (future).
- `rules:write`: Required to call `POST` creation endpoints (future).
- `rules:admin`: Required for administrative actions (future).

### Endpoint Protection Matrix (V6.1.0)
| Endpoint | Method | Required Scope |
| :--- | :--- | :--- |
| `/api/v1/evaluate` | POST | `rules:evaluate` |

## 3. Rate Limiting
- **Policy:** Fixed Window or Token Bucket.
- **Limit:** 100 requests per minute per API Key (configurable).
- **Implementation:** `Microsoft.AspNetCore.RateLimiting` middleware.
- **Response:** HTTP 429 Too Many Requests with `Retry-After` header.
