# RuleForge

**Deterministic - Typed - Sandboxed - Auditable Rule Engine**

RuleForge is a domain-independent rule engine and declarative DSL designed to express business decisions independently from application code.

It provides a deterministic execution model, strict typing, sandboxed actions, schema-aware semantic validation, structured evaluation traces, and a contract-driven architecture designed for cross-language conformance.

---

## Current Status

**V11.2 - Deep AST Trace**

The V11.2 contract introduces a canonical deep evaluation trace that makes rule evaluation structurally observable and auditable.

### Python Implementation
- [x] V11.2 Deep AST Trace implemented
- [x] Canonical NodeType mapping
- [x] AND / OR short-circuit tracing
- [x] Short-circuit phantom nodes
- [x] ANY / ALL tracing
- [x] FILTER / MAP tracing
- [x] Runtime error capture in trace nodes
- [x] RuleTraceEntry.EvaluationTrace
- [x] deep_trace evaluation mode
- [x] 221 tests passing
- [ ] C# V11.2 implementation in progress

The V11.2 contract is defined in CONTRACT_V11_2.md.

---

## Philosophy

RuleForge is not a general-purpose programming language. It is a declarative DSL designed around four core principles:

### Deterministic
Given the same rule, context, schema, and language version, RuleForge produces the same decision.

### Typed
RuleForge uses a strict type system. Type mismatches and invalid operations are detected before execution whenever possible, while runtime type errors are represented through defined evaluator error codes.

### Sandboxed
Rules do not perform external side effects. Actions such as ALLOW, DENY, NO_ACTION, ALERT, APPLY, SET, and EMIT represent declared intent. The host application decides what those actions actually mean.

### Auditable
Rule evaluation can produce a structured Deep AST Trace describing evaluated expressions, operators, values, types, child expressions, short-circuit decisions, and runtime errors. This allows applications to inspect how a decision was reached without embedding business logic into application code.

---

## Architecture

RuleForge follows a layered execution pipeline:

```
Rule Source
    |
    v
+-----------+
|   Lexer   |
+-----+-----+
      |
      v
+-----------+
|  Parser   |
+-----+-----+
      |
      v
+-------------------+
| Semantic Analyzer | <-- Schema
+---------+---------+
          |
          v
+-------------------+
|    Evaluator      |
+---------+---------+
          |
          +--> Decision
          |
          +--> Deep AST Trace
```

### Components

**Lexer** - Tokenizes RuleForge source code.

**Parser** - Builds an Abstract Syntax Tree using recursive descent parsing.

**Semantic Analyzer** - Validates rule structure, types, operators, functions, and context properties against an external schema.

**Evaluator** - Walks the AST and produces deterministic decisions without performing external side effects.

**Engine** - Coordinates parsing, semantic validation, evaluation, action application, and rule-level execution tracing.

---

## V11.2 Deep AST Trace

V11.2 defines a canonical trace representation shared across implementations.

Each trace node contains:

| Field | Type | Description |
|---|---|---|
| NodeType | string | Canonical AST node type |
| Operator | string, optional | Operator or function name |
| Value | any | Serialized result of the node |
| Type | string | RuleForge type of the result |
| Children | list | Traces of evaluated sub-expressions |
| ShortCircuited | bool | True if node was not evaluated due to short-circuit |
| ErrorCode | string, optional | Error code if node failed |
| ErrorMessage | string, optional | Error message if node failed |

### Example: AND short-circuit

Rule:

```
RULE r LANGUAGE 1 WHEN customer.active == true AND customer.age / 0 == 1 THEN ALLOW END
```

Context:

```json
{"customer": {"active": false, "age": 20}}
```

Trace:

```json
{
  "NodeType": "BinaryExpression",
  "Operator": "AND",
  "Value": false,
  "Type": "Boolean",
  "ShortCircuited": false,
  "Children": [
    {
      "NodeType": "BinaryExpression",
      "Operator": "==",
      "Value": false,
      "Type": "Boolean",
      "ShortCircuited": false,
      "Children": []
    },
    {
      "NodeType": "BinaryExpression",
      "Operator": "==",
      "Value": null,
      "Type": "Null",
      "ShortCircuited": true,
      "Children": []
    }
  ]
}
```

When a logical expression short-circuits, the expression that was not evaluated is represented explicitly as a **phantom trace node**:

```
ShortCircuited = true
Value = null
Children = []
```

This makes the trace deterministic while preserving the distinction between an expression that evaluated to null and an expression that was never evaluated.

### Activation

Deep AST Trace is opt-in:

```python
from ruleforge import RuleEngine

engine = RuleEngine(schema)
result = engine.evaluate(source_code, context, trace=True)

# V11.2 contractual path:
# result.trace[0].evaluation_trace
#
# Backward compatible:
# result.decisions[0].trace[0]
```

When trace=False (default), no trace structures are constructed and no tracing overhead is incurred.

When trace=True is requested on a compiled rule, the engine falls back to the interpreted evaluator to produce the trace. The compiler does not instrument the AST.

---

## Canonical AST Node Types

RuleForge maintains a canonical NodeType vocabulary so Python and C# implementations produce equivalent traces.

| AST concept | Canonical NodeType |
|---|---|
| Binary operation | BinaryExpression |
| Unary operation | UnaryExpression |
| Null check | NullCheck |
| Literal | Literal |
| Identifier | Identifier |
| Property access | PropertyExpression |
| Function call | FunctionCall |
| Array literal | ArrayLiteral |
| Array index | ArrayIndex |
| Date literal | DateLiteral |
| ANY / ALL | AnyAll |
| FILTER / MAP | FilterMap |

The canonical vocabulary is independent from the internal class names used by each implementation. Unmapped node types raise RF5004 during development to prevent silent divergence.

---

## Supported Evaluation Features

- Boolean expressions
- Integer and decimal arithmetic
- String operations (concatenation, contains, starts_with, ends_with)
- Date operations (date_add, date_diff, extract)
- Property access
- Null checks (IS NULL / IS NOT NULL)
- Unary operators (NOT)
- Binary operators (==, !=, >, <, >=, <=, +, -, *, /)
- AND / OR with short-circuit evaluation
- Function calls (length, contains, starts_with, ends_with, abs, date_add, date_diff, extract)
- Array literals and indexing
- ANY (short-circuits on first true)
- ALL (short-circuits on first false)
- FILTER (returns matching elements)
- MAP (transforms elements)
- SET (context patching)
- EMIT (intent declaration)
- Structured evaluation traces
- Execution-step limits (MAX_EXECUTION_STEPS = 10000)
- Runtime error codes (RF4001, RF4002, RF4003, RF5003)

---

## Execution Safety

RuleForge enforces an execution step limit of 10000 steps. This provides a runtime guard against pathological or unexpectedly expensive rule evaluation.

Rule actions are declarative and do not directly perform external I/O or application side effects.

---

## Contract-Driven Development

RuleForge development is organized around explicit versioned contracts treated as implementation boundaries rather than informal documentation.

### Version contracts

```
CONTRACT_V8.md          - Initial language contract
CONTRACT_V9.md          - Compiler introduction
CONTRACT_V10.md         - Pipeline and patches
CONTRACT_V10_1.md       - Rule registry
CONTRACT_V10_2.md       - Pipeline trace
CONTRACT_V10_STABLE.md  - V10 stabilization
CONTRACT_V11.md         - Advanced array operations (ANY, ALL)
CONTRACT_V11_1.md       - FILTER and MAP
CONTRACT_V11_2.md       - Deep AST Trace
```

### Subsystem specifications

```
LANGUAGE-SPEC.md
LEXER-SPEC.md
PARSER-SPEC.md
ARRAY-SPEC.md
STRUCTURED-TRACE-SPEC.md
REST-API-SPEC.md
RULE-REGISTRY-SPEC.md
AUTH-SPEC.md
API-HARDENING-SPEC.md
OBSERVABILITY-SPEC.md
ADAPTER-CONTRACT.md
ADAPTER-SPEC.md
ERP-ADAPTER-SPEC.md
FHIR-ADAPTER-SPEC.md
```

---

## Testing

The project uses automated conformance and regression testing across the language pipeline.

Current Python baseline: **221 passed, 1 skipped**.

The test suite covers lexer, parser, semantic analysis, evaluator, rule engine, arrays, functions, dates, runtime errors, API behavior, CLI behavior, adapters, runtime context validation, security limits, structured tracing, short-circuit semantics, and Deep AST Trace.

### V11.2 trace tests

- test_trace_001: simple comparison trace structure
- test_trace_002: logical AND with both children evaluated
- test_trace_003: AND short-circuit with phantom right child
- test_trace_004: null check trace structure
- test_trace_005: AND short-circuit avoids division by zero
- test_trace_006: OR short-circuit with phantom right child
- test_trace_007: FILTER trace with per-item sub-expressions
- test_trace_008: ANY short-circuit with phantom remaining items

---

## Multi-Language Architecture

RuleForge is being developed with Python and C# implementations that conform to the same language and execution contracts.

The goal is not merely to provide two implementations, but to maintain behavioral equivalence between them.

Cross-language validation covers language semantics, evaluation results, error behavior, trace structure, canonical node types, and compiler behavior.

The project includes 61 cross-language conformance vectors covering the shared language and evaluation contracts. The V11.2 trace changes must preserve conformance across Python, C#, and the compiler.

The Python V11.2 Deep AST Trace implementation is complete. The equivalent C# implementation is the next stage of the V11.2 rollout.

---

## Project Structure

```
ruleforge/
|
+-- ruleforge/
|   +-- lexer/
|   +-- parser/
|   +-- semantic/
|   +-- evaluator/
|   +-- compiler/
|   +-- api/
|   +-- engine.py
|
+-- dotnet/
|   +-- src/
|   |   +-- RuleForge.Core/
|   |   +-- RuleForge.Api/
|   |   +-- RuleForge.ConformanceRunner/
|   +-- tests/
|
+-- tests/
|   +-- conformance/
|   |   +-- valid/
|   |   +-- invalid/
|   +-- test_evaluator.py
|   +-- test_engine.py
|   +-- test_trace.py
|   +-- test_conformance.py
|   +-- test_api.py
|
+-- CONTRACT_V8.md to CONTRACT_V11_2.md
+-- *-SPEC.md
+-- README.md
```

---

## Design Principle

RuleForge follows a simple separation of responsibilities:

```
Rules declare intent.
The engine evaluates intent.
The host application performs effects.
```

This keeps business rules portable, testable, deterministic, and independent from the application that consumes them.

---

## Roadmap

### V11.2 - Deep AST Trace

- [x] Deep AST Trace contract (CONTRACT_V11_2.md)
- [x] Canonical Python NodeType mapping
- [x] Python deep trace implementation
- [x] Logical short-circuit tracing (AND, OR)
- [x] ANY / ALL tracing with short-circuit phantoms
- [x] FILTER / MAP tracing with per-element traces
- [x] Runtime error trace metadata
- [x] Python trace test suite (8 tests)
- [x] Engine integration (trace=True activates deep_trace)
- [x] RuleTraceEntry.EvaluationTrace
- [ ] C# TraceNode class
- [ ] C# deep trace evaluator instrumentation
- [ ] C# short-circuit tracing
- [ ] C# ANY / ALL / FILTER / MAP tracing
- [ ] C# trace tests
- [ ] Cross-language V11.2 conformance
- [ ] V11.2.0 release tag

---

## License

See the repository for current licensing terms.
