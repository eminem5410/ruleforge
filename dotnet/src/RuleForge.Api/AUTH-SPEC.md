# RuleForge.NET API Security Specification (V6.2.0)

This document defines the security contract for the RuleForge ASP.NET Core API.
Security is enforced strictly at the HTTP layer using ASP.NET Core Authentication and Authorization.
The `RuleForge.Core` engine remains completely unaware of authentication or authorization.

## 1. Dual Authentication Architecture
The API supports two independent authentication mechanisms. They are mutually exclusive per request but share the same Authorization policies.

### 1.1 API Key (Machine-to-Machine)
- **Scheme:** `ApiKey`
- **Header:** `Authorization: ApiKey <api_key>`
- **Implementation:** Custom `AuthenticationHandler` (`ApiKeyAuthenticationHandler`).

### 1.2 JWT (User/Service Identity)
- **Scheme:** `JwtBearer`
- **Header:** `Authorization: Bearer <jwt_token>`
- **Implementation:** `Microsoft.AspNetCore.Authentication.JwtBearer`.
- **Contract:** See `JWT-SPEC.md` for token structure and validation rules.

## 2. Authorization (Shared)
Authorization is based strictly on scopes, regardless of the authentication mechanism used.
- `rules:evaluate`: Required to call `POST /api/v1/evaluate`.
- `rules:read`: Required to call `GET` endpoints (future).
- `rules:write`: Required to call `POST` creation endpoints (future).
- `rules:admin`: Required for administrative actions (future).

## 3. Endpoint Protection Matrix
| Endpoint | Method | Required Scope |
| :--- | :--- | :--- |
| `/api/v1/evaluate` | POST | `rules:evaluate` |
| `/api/v1/health` | GET | *None (AllowAnonymous)* |

## 4. Rate Limiting
- **Policy:** Fixed Window.
- **Limit:** 100 requests per minute per authenticated identity (API Key ID or JWT `sub`).
- **Implementation:** `Microsoft.AspNetCore.RateLimiting` middleware.
- **Response:** HTTP 429 Too Many Requests with `Retry-After` header (in seconds, rounded up).
