# RuleForge REST API Specification (V3.0.0)

This document defines the contract for the RuleForge HTTP API.
The API acts strictly as a transport adapter. The RuleForge Core remains completely HTTP-agnostic.

## 1. Philosophy
- **Stateless:** The API does not store rules. Clients must send the rule source in every request.
- **Transport Adapter:** FastAPI translates HTTP requests into Python calls to `RuleForgeEngine` and serializes the `Decision` back to JSON.
- **Strict Serialization:** JSON types must strictly adhere to RuleForge's type system (e.g., `Decimal` as string, `Date` as ISO-8601).

## 2. Endpoint: Evaluate Rule
`POST /v1/evaluate`

Evaluates a given rule source against a provided context.

### Request Body
{
  "rules": "RULE adult_check LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END",
  "context": {
    "customer": {
      "age": 21
    }
  },
  "explain": false
}

- `rules` (string, required): The RuleForge source code. Can contain multiple rules.
- `context` (object, required): The domain-agnostic data context.
- `explain` (boolean, optional, default: false): If true, returns the structured trace tree.

### Responses

#### 200 OK (Successful Evaluation)
Returns a list of decisions.
{
  "decisions": [
    {
      "rule_id": "adult_check",
      "rule_version": 1,
      "language_version": 1,
      "matched": true,
      "actions": [
        {
          "type": "ALLOW",
          "value": null
        }
      ],
      "trace": []
    }
  ]
}

#### 400 Bad Request (Rule or Context Error)
Returned when the rule or context fails validation or evaluation (RF1xxx, RF2xxx, RF3xxx, RF4xxx, RF5xxx).
{
  "error": {
    "code": "RF3001",
    "message": "Semantic Error: Cannot compare Integer with String"
  }
}

#### 422 Unprocessable Entity
Returned when the JSON payload is structurally invalid (e.g., missing "rules" or "context" keys).

#### 500 Internal Server Error
Returned for unexpected system failures.

## 3. Serialization Rules
To ensure exact precision and determinism across HTTP boundaries:
- `Integer`: JSON number (e.g., 20)
- `Decimal`: JSON string (e.g., "150000.50")
- `Boolean`: JSON boolean (e.g., true)
- `String`: JSON string
- `Date`: JSON string (ISO 8601, e.g., "1990-05-20")
- `NULL`: JSON null
