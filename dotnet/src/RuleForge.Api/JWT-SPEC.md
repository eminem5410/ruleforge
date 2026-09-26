# RuleForge.NET JWT Specification (V6.2.0)

This document defines the contract for JSON Web Token (JWT) authentication in RuleForge.
For V6.2.0, tokens are signed and validated locally to demonstrate the full cryptographic cycle without external Identity Providers (IdP).

## 1. Token Structure
The JWT must contain the following claims:
- `sub` (string): Subject identifier (e.g., user or service ID). Used for Rate Limiting bucket isolation.
- `scope` (string): Space-separated list of allowed scopes (e.g., `"rules:evaluate rules:read"`).
- `iss` (string): Issuer. Must match `RuleForge:Jwt:Issuer` configuration.
- `aud` (string): Audience. Must match `RuleForge:Jwt:Audience` configuration.
- `exp` (numeric): Expiration time (Unix timestamp). Must be in the future.

## 2. Validation Rules
The API will reject the token (HTTP 401 Unauthorized) if:
1. The signature is invalid (signed with incorrect key or algorithm).
2. The token is expired (`exp` < current time).
3. The issuer (`iss`) does not match the expected issuer.
4. The audience (`aud`) does not match the expected audience.
5. The `scope` claim is missing or empty.

## 3. Authorization Mapping
The `scope` claim (space-separated string) is parsed into individual scope claims (`Claim("scope", value)`) by the JWT handler. 
This ensures the `ScopeHandler` works identically for both API Keys and JWTs.

## 4. Local Signing Configuration
**WARNING:** The configuration below is for Development and Testing ONLY.
- **Algorithm:** HS256 (HMAC using SHA-256).
- **Signing Key:** Configurable via `appsettings.json` (`RuleForge:Jwt:SigningKey`).
- **Issuer:** `ruleforge`
- **Audience:** `ruleforge-api`

**Production Rule:** In production, the `SigningKey` MUST be injected via Environment Variables or a Secret Manager (e.g., Azure Key Vault, AWS Secrets Manager). It must NEVER be committed to source control in plain text.

## 5. Security Test Matrix (JWT)
| Test Case | Expected Result |
| :--- | :--- |
| Valid JWT + `rules:evaluate` scope | 200 OK |
| Expired JWT | 401 Unauthorized |
| Invalid Issuer | 401 Unauthorized |
| Invalid Audience | 401 Unauthorized |
| Valid JWT + Missing `rules:evaluate` scope | 403 Forbidden |
| Invalid Signature (wrong key) | 401 Unauthorized |
| Two JWTs with same `sub` share Rate Limit bucket | 429 on 101st request for either token |
