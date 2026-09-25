# RuleForge Structured Trace Specification

This document defines the contract for the structured trace output in RuleForge V1.4.0.
Traces are no longer human-readable strings; they are semantic JSON trees that allow external systems (dashboards, APIs) to reconstruct exactly how a decision was reached.

## 1. Trace Model
When `explain_mode=True`, the `Decision.trace` will contain a list of structured trace events. 
The root event usually corresponds to the top-level expression of the `WHEN` condition.
Nested events represent the evaluation of sub-expressions.

## 2. Event Types
Every event is a JSON object with a `type` field.

### 2.1. Literal
{"type": "literal", "value": 20, "data_type": "Integer"}

### 2.2. Property Access
{"type": "property", "path": "customer.age", "value": 20}

### 2.3. Comparison
{"type": "comparison", "operator": ">=", "left": <event>, "right": <event>, "result": true}

### 2.4. Arithmetic
{"type": "arithmetic", "operator": "+", "left": <event>, "right": <event>, "result": 120}

### 2.5. Logical (AND / OR)
{"type": "logical", "operator": "AND", "left": <event>, "right": <event>, "result": true}

### 2.6. Unary (NOT)
{"type": "unary", "operator": "NOT", "operand": <event>, "result": false}

### 2.7. Null Check
{"type": "null_check", "operator": "IS NULL", "value": <event>, "result": true}

### 2.8. Function Call
{"type": "function", "name": "contains", "arguments": [<event>, <event>], "result": true}

### 2.9. Short-Circuit
When an AND or OR short-circuits, the right side is not evaluated.
{"type": "short_circuit", "operator": "AND", "left": <event>, "result": false}

## 3. Decision Trace Integration
The Decision.to_dict() method will return the trace as a list of these event objects.
A UI can recursively walk `left`, `right`, `operand`, `value`, and `arguments` to render the evaluation tree.
