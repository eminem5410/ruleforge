# RuleForge REST API Specification (V3.0.2)

This document defines the contract for the RuleForge HTTP API.
The API acts strictly as a transport adapter. The RuleForge Core remains completely HTTP-agnostic.

## 1. Philosophy
- **Stateless:** The API does not store rules. Clients must send the rule source in every request.
- **Transport Adapter:** FastAPI translates HTTP requests into Python calls to `RuleForgeEngine` and serializes the `Decision` back to JSON.
- **Strict Serialization:** JSON types must strictly adhere to RuleForge's type system (e.g., `Decimal` as string, `Date` as ISO-8601).

## 2. Endpoint: Evaluate Rule
`POST /v1/evaluate`

### Request Body
{
  "rules": "RULE adult_check LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END",
  "context": {
    "customer": {
      "age": 21,
      "balance": "1500.50",
      "birth_date": "1990-05-20"
    }
  },
  "context_schema": {
    "customer": {
      "age": "Integer",
      "balance": "Decimal",
      "birth_date": "Date"
    }
  },
  "explain": false
}

- `rules` (string, required): The RuleForge source code.
- `context` (object, required): The domain-agnostic data context.
- `context_schema` (object, required): The type schema for the context. The API uses this to normalize JSON types (e.g., string to Decimal) before passing to the Core.
- `explain` (boolean, optional, default: false): If true, returns the structured trace tree.

### Responses
#### 200 OK
{
  "decisions": [
    {
      "rule_id": "adult_check",
      "rule_version": 1,
      "language_version": 1,
      "matched": true,
      "actions": [{"type": "ALLOW", "value": null}],
      "trace": []
    }
  ]
}

#### 400 Bad Request (RF ExErrors)
#### 422 Unprocessable Entity (Missing fields)
#### 500 Internal Server Error

## 3. API Type Normalization
To bridge JSON and RuleForge Core, the API normalizes incoming context data based on `context_schema`:
- `Decimal`: Converted from JSON string/number to Python `decimal.Decimal`.
- `Date`: Passed as ISO-8601 string. The RuleForge Core handles the conversion to `datetime.date` internally.
