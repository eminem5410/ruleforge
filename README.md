# RuleForge

**Deterministic - Typed - Sandboxed - Auditable Rule Engine**

RuleForge is a domain-independent rule engine and declarative DSL designed to express business decisions independently from application code.

It provides a deterministic execution model, strict typing, sandboxed actions, schema-aware semantic validation, structured evaluation traces, compiler support, runtime safety limits, and contract-driven cross-language conformance between Python and C# implementations.

---

## Current Status

**V11.5.0 - Compiler Performance & Runtime Semantics**

V11.5.0 eliminates a quadratic evaluation bottleneck in the compiled execution pipeline while preserving RuleForge's sequential rule semantics.

### V11.5.0

- [x] Sequential SET semantics frozen with regression tests
- [x] Compiler pipeline quadratic evaluation identified
- [x] RuleForgeCompiler.execute_single() implemented
- [x] Engine no longer re-evaluates the complete rule set for every rule
- [x] Sequential context mutation preserved
- [x] Compiler/interpreter semantic equivalence validated
- [x] Cross-language conformance validated
- [x] Compiler conformance validated
- [x] Runtime and regression suite validated
- [x] V11.5.0 release tagged

### Current test baseline

| Suite | Result |
|---|---|
| Python | 288 passed, 1 skipped |
| C# Core | 150 passed |
| C# API | 18 passed |
| Cross-language conformance | 61/61 MATCH |
| Compiler conformance | 61/61 MATCH |
| Compiler invariant testing | 1000 examples |
| V11.5 sequential SET regression | 12/12 passed |

### Compiler scaling

The V11.4 compiler pipeline could re-evaluate the complete rule set once per rule.

For N rules:

```
rule 1 -> evaluate all N rules
rule 2 -> evaluate all N rules
...
rule N -> evaluate all N rules

Total: O(N^2)
```

V11.5 evaluates each rule directly:

```
rule 1 -> execute_single(rule 1)
rule 2 -> execute_single(rule 2)
...
rule N -> execute_single(rule N)

Total pipeline rule evaluation: O(N)
```

Observed scaling:

| Rules | V11.4 | V11.5 |
|---|---|---|
| 250 | ~76 ms | ~17 ms |
| 500 | ~300 ms | ~34 ms |
| 1000 | - | ~69 ms |

The benchmark demonstrates linear scaling of the affected compiler pipeline with respect to rule count.

---

## Philosophy

RuleForge is not a general-purpose programming language. It is a declarative DSL designed around four core principles:

### Deterministic
Given the same rules, context, schema, and language version, RuleForge produces the same decision.

### Typed
RuleForge uses a strict type system. Type mismatches and invalid operations are detected before execution whenever possible.

### Sandboxed
Rules do not perform external side effects. Actions such as ALLOW, DENY, NO_ACTION, ALERT, APPLY, SET, and EMIT represent declared intent.

### Auditable
Rule evaluation can produce structured traces describing evaluated expressions, operators, values, types, child expressions, short-circuit decisions, and runtime errors.

---

## Architecture

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
          +--> Evaluation Trace
          |
          +--> Applied Patches
```

The compiler provides an optimized execution path for supported expressions while preserving the same observable semantics as the interpreter.

### Components

**Lexer** - Tokenizes RuleForge source code.
**Parser** - Builds an Abstract Syntax Tree using recursive descent parsing.
**Semantic Analyzer** - Validates rule structure, types, operators, functions, and context properties against an external schema.
**Evaluator** - Walks the AST and produces deterministic decisions without performing external side effects.
**Compiler** - Compiles supported condition expressions into a sandboxed executable representation and provides optimized rule execution.
**Engine** - Coordinates parsing, semantic validation, evaluation, action application, sequential context updates, tracing, and rule-level execution.

---

## Sequential Rule Semantics

RuleForge evaluates rules sequentially. This is particularly important for SET, because a rule may modify the working context that subsequent rules observe.

Example:

```
RULE first LANGUAGE 1
WHEN customer.active == true
THEN
    SET customer.status = "blocked"
END

RULE second LANGUAGE 1
WHEN customer.status == "blocked"
THEN
    DENY
END
```

The second rule sees the context produced by the first rule.

V11.5 explicitly freezes this behavior with regression tests covering:

- basic SET visibility
- non-matching rules
- chained SET operations
- prevention of future-state leakage
- multiple SET operations
- SET followed by DENY

The same semantics are validated through both interpreter and compiler execution.

---

## Compiler Execution

The compiler supports optimized condition evaluation while preserving the interpreter's observable behavior.

Prior to V11.5, the engine could effectively execute the complete compiled rule pipeline for every individual rule:

```
compiler.execute(working_context)[i]
```

This caused unnecessary repeated evaluation.

V11.5 introduces:

```
compiler.execute_single(rule, working_context)
```

The engine now evaluates the current rule directly and continues with the updated working context. This removes the quadratic pipeline re-evaluation without changing sequential rule semantics.

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
- FILTER / MAP
- SET / EMIT
- Structured evaluation traces
- Deep AST tracing
- Execution-step limits
- Runtime error codes
- Schema-aware context validation

---

## Deep AST Trace

Each trace node contains:

| Field | Type | Description |
|---|---|---|
| NodeType | string | Canonical AST node type |
| Operator | string, optional | Operator or function name |
| Value | any | Serialized result |
| Type | string | RuleForge type |
| Children | list | Traces of evaluated sub-expressions |
| ShortCircuited | bool | Whether evaluation was skipped |
| ErrorCode | string, optional | Runtime error code |
| ErrorMessage | string, optional | Runtime error message |

### Short-circuit tracing

For A AND B where A is false, B is represented as a phantom trace node:

```
{
  "ShortCircuited": true,
  "Value": null,
  "Children": []
}
```

### Activation

```
from ruleforge import RuleEngine

engine = RuleEngine(schema)
result = engine.evaluate(source_code, context, trace=True)
```

---

## Canonical AST Node Types

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

Unmapped node types raise RF5004 during development to prevent silent divergence.

---

## Execution Safety

```
MAX_EXECUTION_STEPS = 10000
```

Rules do not perform external I/O or application side effects directly.

---

## Contract-Driven Development

```
CONTRACT_V8.md       - Initial language contract
CONTRACT_V9.md       - Compiler introduction
CONTRACT_V10.md      - Pipeline and patches
CONTRACT_V10_1.md    - Rule registry
CONTRACT_V10_2.md    - Pipeline trace
CONTRACT_V10_STABLE  - V10 stabilization
CONTRACT_V11.md      - ANY / ALL
CONTRACT_V11_1.md    - FILTER and MAP
CONTRACT_V11_2.md    - Deep AST Trace
CONTRACT_V11_3.md    - Trace contract hardening
CONTRACT_V11_4.md    - Runtime safety and determinism
```

V11.5 focuses on implementation-level compiler performance while preserving the previously frozen language and runtime contracts.

---

## Testing

### Current V11.5.0 baseline

```
Python:     288 passed, 1 skipped
C# Core:    150 passed
C# API:     18 passed
Cross-language: 61/61 MATCH
Compiler:   61/61 MATCH
```

### Compiler invariant testing

1000 examples: Interpreter == Compiler

### Sequential semantics

12 tests: 6 scenarios x 2 execution modes (interpreter + compiler)

### Full validation

```
Python tests -> C# Core -> C# API -> Cross-language -> Compiler conformance
```

---

## Multi-Language Architecture

RuleForge is developed with Python and C# implementations that conform to the same language and execution contracts.

```
61 / 61 cross-language vectors: MATCH
61 / 61 compiler vectors: MATCH
```

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
|   +-- property/
|   +-- test_evaluator.py
|   +-- test_engine.py
|   +-- test_trace.py
|   +-- test_sequential_semantics.py
|
+-- CONTRACT_V8.md to CONTRACT_V11_4.md
+-- *-SPEC.md
+-- README.md
```

---

## Design Principle

```
Rules declare intent.
The engine evaluates intent.
The engine produces decisions and patches.
The host application performs effects.
```

---

## Roadmap

### Completed

- [x] V11.0 - ANY / ALL
- [x] V11.1 - FILTER / MAP
- [x] V11.2 - Deep AST Trace
- [x] V11.3 - Trace Contract Hardening
- [x] V11.4 - Runtime Safety & Determinism
- [x] V11.5 - Compiler Performance

### Next

- Compiler execution architecture refinement
- Shared execution logic between execute() and execute_single()
- Additional performance profiling
- Broader property-based compiler testing
- Continued Python/C# conformance expansion

---

## Release

Current release: v11.5.0

---

## License

See the repository for current licensing terms.

## Tooling

RuleForge provides a command-line interface for validating, evaluating,
and diagnosing rule files.

### Evaluate

Get the business decision for a given context.

```bash
ruleforge eval rules.rf --context '{"customer":{"age":25}}'
Validate (Check)

Validate syntax and semantics without evaluating.
ruleforge check rules.rf --schema '{"customer":{"age":"Integer"}}'
Trace

Understand how each rule was evaluated step-by-step.
ruleforge trace rules.rf --context '{"customer":{"age":25}}'
Exit Codes
0: Operation successful.
1: Validation, evaluation, or input error.

