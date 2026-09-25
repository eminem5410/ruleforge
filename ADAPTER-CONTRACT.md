# RuleForge Adapter Contract (V2.1.0)

This document defines the strict operational contract that any RuleForge Adapter (FHIR, ERP, Custom) must obey.

## 1. Pipeline Architecture
Domain Object (e.g., FHIR Resource, DB Entity)
      ↓
Adapter.to_context()
      ↓
Generic RuleForge Context (JSON)
      ↓
RuleForgeEngine.evaluate()
      ↓
Decision (JSON)
      ↓
Host Application
      ↓
Execute declared action

## 2. Adapter Responsibilities
An adapter is strictly responsible for:
- **Translation:** Mapping domain-specific fields to a generic RuleForge context.
- **Structure Validation:** Ensuring the minimum required data exists before passing it to the engine.
- **Type Normalization:** Converting numbers to `Decimal` to preserve exact precision.
- **Deterministic Dates:** Converting dates explicitly (e.g., calculating age using a provided `reference_date`, never `date.today()`).
- **Missing Data Representation:** Mapping missing or unknown domain values to `NULL` (None in Python). Adapters must NOT invent default domain values (e.g., defaulting missing "status" to "UNKNOWN").

## 3. Adapter Prohibitions (The Golden Rules)
An adapter MUST NOT:
- **Execute Actions:** Adapters do not execute side effects (no DB writes, no API calls).
- **Contain Business Logic:** Adapters must not contain decision logic (e.g., `if patient.age > 65`). That belongs in `.rf` rules.
- **Access Infrastructure:** Adapters should not access the database or call external services directly.
- **Bypass the Engine:** Adapters must never evaluate rules themselves.

## 4. Host Application Responsibilities
The Host (Vantari, ContaFlow, etc.) is responsible for:
- Providing the domain data to the adapter.
- Calling `RuleForgeEngine.evaluate()`.
- Receiving the `Decision`.
- Deciding what `APPLY "AUTO_APPROVE"` actually means in the database or API.
