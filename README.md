# RuleForge

[English](./README.md) | [Español](./README.es.md)

<p align="center">
  <strong>Deterministic, typed, sandboxed, and auditable rule execution<br>
  for applications that need predictable policy decisions.</strong>
</p>

<p align="center">
  <img alt="Stable release" src="https://img.shields.io/badge/release-v12.0.0-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.8+-green">
  <img alt=".NET" src="https://img.shields.io/badge/.NET-Core-success">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
  <img alt="Status" src="https://img.shields.io/badge/status-stable-brightgreen">
</p>

---

## Table of Contents

- [Design Principle](#design-principle)
- [Architecture](#architecture)
- [Interpreter and Compiler](#interpreter-and-compiler)
- [Supported Language Features](#supported-language-features)
- [Evaluation Trace](#evaluation-trace)
  - [MATCH Trace Contract](#match-trace-contract)
- [Short-Circuit Evaluation](#short-circuit-evaluation)
- [Security and Runtime Safety](#security-and-runtime-safety)
- [Contract-Driven Development](#contract-driven-development)
- [Cross-Language Architecture](#cross-language-architecture)
- [V12.0.0 Quality Gate](#v1200-quality-gate)
- [Tooling](#tooling)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Development and Quality Gates](#development-and-quality-gates)
- [Language Evolution Rules](#language-evolution-rules)
- [Roadmap](#roadmap)
- [Architectural Baseline](#architectural-baseline)
- [Release](#release)

---

## Design Principle

> Rules declare **intent**.
> The engine evaluates intent.
> The engine produces decisions and patches.
> The host application performs effects.

This separation is fundamental to RuleForge's security and determinism model. The rule engine never executes side effects directly — it produces structured decisions and patches that the host application is responsible for applying. This guarantees that rule evaluation remains observable, reproducible, and safe to run in sensitive workloads.

---

## Architecture

RuleForge is structured as a layered pipeline. Each layer has a single, well-defined responsibility and produces an artifact consumed by the next layer. This separation enables independent testing, conformance verification, and cross-language parity.

```text
                         Rule Source
                              |
                              v
                       +--------------+
                       |    Lexer     |
                       +------+-------+
                              |
                              v
                       +--------------+
                       |    Parser    |
                       +------+-------+
                              |
                              v
                  +--------------------------+
                  |    Semantic Analyzer     |
                  |                          |
                  |        + Schema          |
                  +------------+-------------+
                               |
                               v
                       +---------------+
                       |   Evaluator   |
                       +-------+-------+
                               |
                +--------------+--------------+
                |              |              |
                v              v              v
            Decision         Trace        Patches
```

The compiler provides an optimized execution path while preserving the same observable semantics as the interpreter.

### Components

| Component          | Responsibility                                                                                       |
|--------------------|-------------------------------------------------------------------------------------------------------|
| **Lexer**          | Tokenizes RuleForge source code.                                                                      |
| **Parser**         | Builds the Abstract Syntax Tree using recursive descent parsing.                                     |
| **Semantic Analyzer** | Validates rule structure, types, operators, functions, context properties, MATCH/CASE compatibility, duplicate CASE values, and execution constraints against the supplied schema and language contract. |
| **Evaluator**     | Executes the AST under RuleForge's deterministic runtime model.                                       |
| **Compiler**       | Provides optimized condition execution while preserving interpreter semantics.                       |
| **Engine**         | Coordinates parsing, semantic validation, evaluation, sequential state updates, decision generation, tracing, patches, and runtime error handling. |

---

## Interpreter and Compiler

RuleForge maintains two execution paths. Both are required to preserve semantic equivalence — any divergence between them is treated as a release-blocking defect.

```text
Rule Source
     |
     +------------------+
     |                  |
     v                  v
 Interpreter         Compiler
     |                  |
     +--------+---------+
              |
              v
        Observable Result
```

**V11.5** removed an unnecessary quadratic evaluation pattern from the compiled pipeline by introducing direct per-rule execution through:

```python
execute_single(rule, working_context)
```

This preserved sequential `SET` semantics while avoiding repeated evaluation of the complete rule set.

**V12.0.0** builds on that execution architecture.

---

## Supported Language Features

Current RuleForge language support includes:

- Boolean expressions
- Integer arithmetic
- Decimal arithmetic
- String operations
- Date operations
- Property access
- Null checks
- Unary operators
- Binary operators
- `AND` / `OR` short-circuit evaluation
- Function calls
- Array literals
- Array indexing
- `ANY`, `ALL`, `FILTER`, `MAP`
- `SET`, `EMIT`
- `MATCH`, `CASE`, `DEFAULT`
- Structured evaluation traces
- Deep AST tracing
- Runtime execution limits
- Schema-aware validation

---

## Evaluation Trace

Tracing is part of the RuleForge observability contract.

A trace can describe the evaluation of expressions and decisions without changing the underlying semantics. This makes traces safe to ship to logs, audit pipelines, and debugging tools without risking behavioral divergence between traced and untraced execution.

| Field            | Description                              |
|------------------|------------------------------------------|
| `NodeType`       | Canonical AST node type                  |
| `Operator`       | Operator or function                     |
| `Value`          | Serialized result                       |
| `Type`           | RuleForge type                           |
| `Children`       | Evaluated child expressions              |
| `ShortCircuited` | Whether evaluation was skipped           |
| `ErrorCode`      | Runtime error code                       |
| `ErrorMessage`   | Runtime error message                    |

### MATCH Trace Contract

For `MATCH`:

- The `MATCH` expression is evaluated exactly once.
- Its resulting value and type are recorded.
- `CASE` expressions are evaluated sequentially.
- Evaluation stops at the first match.
- Later `CASE` branches are represented as short-circuited rather than falsely evaluated.
- If no `CASE` matches, `DEFAULT` is selected when present.
- If no `CASE` matches and no `DEFAULT` exists, the rule produces `NO_ACTION`.
- `SET` and `EMIT` remain actions rather than artificial trace nodes.
- Runtime errors preserve the established error trace contract.

This behavior is defined in [`docs/rfc/RFC-001-MATCH-CASE.md`](docs/rfc/RFC-001-MATCH-CASE.md).

---

## Short-Circuit Evaluation

RuleForge explicitly models short-circuit behavior. This is part of the language contract, not an optimization — the runtime guarantees that skipped branches are not evaluated and that their omission is observable in the trace.

For `A AND B`, when `A` is false, `B` is not evaluated.

The trace records the skipped branch as:

```json
{
  "ShortCircuited": true,
  "Reason": "short_circuit"
}
```

The same principle applies to supported short-circuiting constructs such as `AND`, `OR`, `ANY`, `ALL`, and `MATCH` branch selection.

---

## Security and Runtime Safety

RuleForge is intentionally constrained. The language is designed for environments where predictability matters more than expressiveness — policy evaluation, compliance, fraud detection, and similar workloads where a non-deterministic result is a defect, not a performance concern.

The execution model provides:

- Bounded execution
- Strict typing
- AST safety limits
- Controlled action semantics
- Schema-aware validation
- No direct external side effects
- Deterministic evaluation
- Runtime error codes
- Traceable execution

> The language is **not** intended to be Turing-complete.
> This is a deliberate design decision.
> Predictability is treated as a language invariant rather than an optimization.

---

## Contract-Driven Development

RuleForge evolves through explicit contracts and RFCs. Every non-trivial behavior is documented before it is implemented, and every implementation is held accountable to its contract through conformance vectors.

Historical contracts include `CONTRACT_V8.md` through `CONTRACT_V11_4.md`.

**V12.0.0** introduces:

```
docs/rfc/RFC-001-MATCH-CASE.md
```

The architectural state of the stable release is documented in:

```
docs/architecture/V12.0.0-BASELINE.md
```

---

## Cross-Language Architecture

RuleForge has independent Python and C# implementations operating against the same language contracts.

The objective is **not** merely API compatibility. The implementations must agree on parsing behavior, semantic validation, decisions, errors, patches, traces, and compiler behavior.

Cross-language conformance is therefore treated as a **release gate** — a release is not cut if Python and C# disagree on any observed behavior in the conformance vectors.

---

## V12.0.0 Quality Gate

The stable V12.0.0 release was validated through multiple independent layers. Each layer is a separate gate; failure in any one blocks the release.

| Validation                       | Result              |
|----------------------------------|---------------------|
| Python Core + Conformance        | 361 passed, 1 skipped |
| C# Core                          | 158/158             |
| C# API                           | 18/18               |
| Cross-language conformance       | 69/69 MATCH         |
| Compiler conformance             | 69/69 MATCH         |
| MATCH/CASE vectors               | 8/8                 |
| MATCH trace tests                | 6/6                 |
| Interpreter/Compiler parity      | 5/5                 |

Cross-language and compiler conformance: **69 / 69 MATCH (100%)**.

MATCH/CASE conformance:

- 6 valid vectors
- 2 invalid vectors
- 8 / 8 validated

The release also preserves the V11 regression suite.

---

## Tooling

RuleForge provides a CLI for validation, evaluation, and tracing.

**Evaluate:**

```bash
ruleforge eval rules.rf --context '{"customer":{"age":25}}'
```

**Validate:**

```bash
ruleforge check rules.rf --schema '{"customer":{"age":"Integer"}}'
```

**Trace:**

```bash
ruleforge trace rules.rf --context '{"customer":{"age":25}}'
```

**Help:**

```bash
ruleforge --help
```

---

## Installation

Install the Python package from the repository:

```bash
pip install .
```

For development:

```bash
pip install -e .
```

The project also contains the .NET implementation and conformance infrastructure.

---

## Project Structure

```text
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
|   |
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
+-- docs/
|   +-- rfc/
|   +-- architecture/
|
+-- CONTRACT_*.md
+-- README.md
+-- README.es.md
```

---

## Development and Quality Gates

RuleForge follows a layered validation strategy. Each layer gates the next — a regression at any level prevents progression to the subsequent layer.

```text
Python tests
      |
      v
C# Core tests
      |
      v
C# API tests
      |
      v
Cross-language conformance
      |
      v
Compiler conformance
      |
      v
Release gate
```

> A language feature is **not** considered complete until its behavior is validated across the relevant implementation layers.

---

## Language Evolution Rules

Future language changes follow these principles:

| Principle                  | Description                                                                                          |
|----------------------------|------------------------------------------------------------------------------------------------------|
| **RFC First**              | Non-trivial language features are specified before implementation.                                   |
| **Layer by Layer**         | Lexer → AST → Semantic → Evaluator → Trace.                                                         |
| **Cross-Language Parity**  | Python and C# must agree on observable behavior.                                                     |
| **V11/V12 Isolation**      | New features should avoid unnecessary global changes to established execution paths.                |
| **Conformance as a Gate** | A feature is not complete until its behavior is represented in conformance vectors and tests.       |

---

## Roadmap

### Completed

- **V11.0** — ANY / ALL
- **V11.1** — FILTER / MAP
- **V11.2** — Deep AST Trace
- **V11.3** — Trace Contract Hardening
- **V11.4** — Runtime Safety & Determinism
- **V11.5** — Compiler Performance & Sequential Runtime Semantics
- **V11.7** — AST Cache
- **V11.8** — Runtime and trace performance work
- **V11.9** — CLI, REPL, tooling, and API decoupling
- **V12.0** — MATCH / CASE

### Future Considerations

Potential future work includes JSON Schema integration, additional language expressiveness, pattern matching, and further compiler/runtime optimization.

> A general-purpose looping construct such as `FOR EACH` remains deliberately deferred because it would require revisiting RuleForge's bounded, non-Turing-complete execution model.

> Future items are design considerations, **not commitments** to a specific release.

---

## Architectural Baseline

The stable V12.0.0 architecture is frozen and documented in:

```
docs/architecture/V12.0.0-BASELINE.md
```

This document records:

- V11.8 → V12.0 evolution
- RFC-001 invariants
- Architectural integration
- Trace contract
- Quality gate results
- Discarded decisions
- Future considerations
- Rules for future language evolution

---

## Release

**Current stable release:** `v12.0.0`

---

<p align="center">
  <sub>RuleForge — Deterministic rule execution for predictable policy decisions.</sub>
</p>
