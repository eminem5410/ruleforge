# RuleForge Cross-Language Conformance Contract (v1.0)

This document defines the canonical contract for RuleForge language version 1.
Any implementation (Python, C#, Rust, etc.) MUST adhere to these rules to be considered compliant.

## 1. Contract & Language Versions
- **Contract Version:** 1.0
- **Language Version:** 1

## 2. Input Vector Format
Vectors are defined in JSON files with the following structure:
{
  "id": "RF-CONF-XXX",
  "name": "Description",
  "source": "RULE ... END",
  "context_schema": { "object_name": { "prop_name": "Type" } },
  "context": { "object_name": { "prop_name": <value> } },
  "expected": { "status": "ok|error", ... }
}

## 3. Supported Types
- `Integer`: Whole numbers.
- `Decimal`: Exact decimal numbers (no floating-point approximations).
- `String`: UTF-8 text.
- `Boolean`: `true` or `false`.
- `Date`: Calendar dates (no time/timezone).

## 4. Canonical Serialization (JSON Output)
To ensure exact 1:1 matching across languages, all implementations must serialize their output as follows:
- **Integer**: JSON number (e.g., `21`)
- **Decimal**: JSON string to preserve precision (e.g., `"150.50"`)
- **String**: JSON string (e.g., `"Pablo"`)
- **Boolean**: JSON boolean (`true` or `false`)
- **Date**: JSON string in ISO 8601 format (`YYYY-MM-DD`, e.g., `"1990-05-20"`)
- **Null/None**: JSON `null`

## 5. Decision Output (Success)
If evaluation succeeds, the output MUST be:
{
  "status": "ok",
  "decisions": [
    {
      "rule_id": "<string>",
      "matched": <boolean>,
      "actions": [
        { "type": "<string>", "value": <string|null> }
      ]
    }
  ]
}

## 6. Error Contract (Failure)
If evaluation fails (Lexical, Parse, Semantic, or Runtime), the output MUST be:
{
  "status": "error",
  "error_code": "RFXXXX"
}
Error categories:
- RF1xxx: Lexical
- RF2xxx: Parse
- RF3xxx: Semantic / Type
- RF4xxx: Runtime
- RF5xxx: Security / Limits

## 7. NULL Semantics
- Missing properties in the runtime context MUST be evaluated as `NULL`.
- `NULL` arithmetic or comparison (e.g., `NULL + 10`, `NULL == 1`) MUST raise `RF4002` (Runtime Type Error).
- `IS NULL` and `IS NOT NULL` are the ONLY valid operations for `NULL`.

## 8. Determinism
Given the same `source`, `context_schema`, `context`, and `language_version`, the implementation MUST produce the exact same canonical output.
