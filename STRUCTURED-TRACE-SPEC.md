# RuleForge Structured Trace Specification

This document defines the contract for the structured trace output in RuleForge V1.4.x.
Traces are semantic JSON trees that allow external systems (dashboards, APIs) to reconstruct exactly how a decision was reached.

## 1. Trace Model
When `explain_mode=True`, the `Decision.trace` will contain a list of structured trace events. 
The root event usually corresponds to the top-level expression of the `WHEN` condition.
Nested events represent the evaluation of sub-expressions.

## 2. JSON Serialization Rules
To ensure deterministic consumption by external systems (like React dashboards or APIs), values in the trace MUST adhere to the following JSON types:

- `Integer`: JSON number (e.g., `20`)
- `Decimal`: JSON string (e.g., `"100.50"`) to preserve exact precision.
- `Boolean`: JSON boolean (e.g., `true` or `false`), NOT strings.
- `String`: JSON string (e.g., `"Pablo"`)
- `Date`: JSON string in ISO 8601 format (e.g., `"1990-05-20"`)
- `NULL`: JSON `null`

## 3. Event Types
Every event is a JSON object with a `type` field.

### 3.1. Literal
{"type": "literal", "value": 20, "data_type": "Integer"}
For booleans: {"type": "literal", "value": true, "data_type": "Boolean"}

### 3.2. Property Access
{"type": "property", "path": "customer.age", "value": 20}

### 3.3. Comparison
{"type": "comparison", "operator": ">=", "left": <event>, "right": <event>, "result": true}

### 3.4. Arithmetic
{"type": "arithmetic", "operator": "+", "left": <event>, "right": <event>, "result": 120}

### 3.5. Logical (AND / OR)
{"type": "logical", "operator": "AND", "left": <event>, "right": <event>, "result": true}

### 3.6. Unary (NOT)
{"type": "unary", "operator": "NOT", "operand": <event>, "result": false}

### 3.7. Null Check
{"type": "null_check", "operator": "IS NULL", "value": <event>, "result": true}

### 3.8. Function Call
{"type": "function", "name": "contains", "arguments": [<event>, <event>], "result": true}

### 3.9. Short-Circuit
When an AND or OR short-circuits, the right side is not evaluated.
{"type": "short_circuit", "operator": "AND", "left": <event>, "result": false}
