# RuleForge

[English](README.md) | [Español](README.es.md)

[![Status: Stable](https://img.shields.io/badge/Status-Stable-brightgreen)](https://github.com/eminem5410/ruleforge/releases/tag/v12.0.0)
[![Python Tests](https://img.shields.io/badge/Python_Tests-361%20passed-blue)](https://github.com/eminem5410/ruleforge)
[![C# Tests](https://img.shields.io/badge/C%23_Tests-176%20passed-blue)](https://github.com/eminem5410/ruleforge)
[![Cross-Language Conformance](https://img.shields.io/badge/Cross_Language-100%25%20MATCH-success)](https://github.com/eminem5410/ruleforge)

RuleForge is a deterministic, strongly typed, and sandboxed rule engine. It evaluates business rules with zero ambiguity, ensuring that Python and C# implementations produce identical results.

## Why RuleForge?

- **Deterministic & Bounded:** No loops, no recursion, no side effects. Every rule evaluation is guaranteed to terminate within strict execution limits.
- **Strongly Typed:** Semantic analysis rejects type mismatches at compile time (e.g., comparing an Integer to a String).
- **Cross-Language:** Write rules once; execute them in Python or .NET/C# with 100% identical decisions and traces.
- **Compiler Parity:** The Interpreter and the Compiler are proven to be mathematically equivalent through 69/69 conformance vectors.

## Language Example (V12.0.0)

```ruleforge
RULE customer_status LANGUAGE 1
MATCH customer.status
CASE "ACTIVE":
    ALLOW
CASE "BLOCKED":
    DENY "Access blocked"
DEFAULT:
    NO_ACTION
END
Tooling (CLI & REPL)
RuleForge provides a native CLI for validating, evaluating, and tracing rules.

Evaluate
ruleforge eval rules.rf --context '{"customer":{"age":25}}'
Validate (Check)
ruleforge check rules.rf --schema '{"customer":{"age":"Integer"}}'
Trace
ruleforge trace rules.rf --context '{"customer":{"age":25}}'
Architecture & Documentation
V12.0.0 Architectural Baseline
RFC-001: MATCH / CASE
Installation
pip install .
Quality Gate Results (V12.0.0)
Python Core + Conformance: 361 passed, 1 skipped
C# Core: 158/158 passed
C# API: 18/18 passed
Cross-Language Conformance: 69/69 MATCH (100%)
Compiler Conformance: 69/69 MATCH (100%)
