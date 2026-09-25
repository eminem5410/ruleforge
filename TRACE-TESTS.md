# RuleForge Structured Trace Conformance Tests

## TRACE-001: Simple Comparison
Rule: WHEN customer.age >= 18
Context: {"customer": {"age": 20}}
Expected Trace:
[
  {
    "type": "comparison", "operator": ">=",
    "left": {"type": "property", "path": "customer.age", "value": 20},
    "right": {"type": "literal", "value": 18, "data_type": "Integer"},
    "result": true
  }
]

## TRACE-002: Logical AND
Rule: WHEN customer.age >= 18 AND customer.active == true
Context: {"customer": {"age": 20, "active": True}}
Expected Trace:
[
  {
    "type": "logical", "operator": "AND",
    "left": {
      "type": "comparison", "operator": ">=",
      "left": {"type": "property", "path": "customer.age", "value": 20},
      "right": {"type": "literal", "value": 18, "data_type": "Integer"},
      "result": true
    },
    "right": {
      "type": "comparison", "operator": "==",
      "left": {"type": "property", "path": "customer.active", "value": true},
      "right": {"type": "literal", "value": "true", "data_type": "Boolean"},
      "result": true
    },
    "result": true
  }
]

## TRACE-003: Short-Circuit AND
Rule: WHEN customer.active == false AND customer.age / 0 == 1
Context: {"customer": {"active": False, "age": 20}}
Expected Trace:
[
  {
    "type": "short_circuit", "operator": "AND",
    "left": {
      "type": "comparison", "operator": "==",
      "left": {"type": "property", "path": "customer.active", "value": false},
      "right": {"type": "literal", "value": "false", "data_type": "Boolean"},
      "result": true
    },
    "result": false
  }
]

## TRACE-004: Null Check
Rule: WHEN customer.email IS NULL
Context: {"customer": {}}
Expected Trace:
[
  {
    "type": "null_check", "operator": "IS NULL",
    "value": {"type": "property", "path": "customer.email", "value": null},
    "result": true
  }
]
