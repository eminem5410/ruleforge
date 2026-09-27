# RuleForge V9.0 — Compilation / Optimization Contract

This document is the normative specification for the V9.0 evolution. 
V9 introduces a compilation phase to optimize execution throughput, but it strictly preserves V7/V8 semantics.

## 1. Golden Rule (Constitutional Clause)
**Optimization MUST be semantics-preserving.**
During V9, the Interpreter remains the normative execution reference. 
For any given rule and context, the compiled execution MUST produce the exact same observable result (decisions, actions, EMIT payloads, and error codes) as the interpreted execution.

```text
Interpreter(rule, context) == Compiled(rule, context)
2. Architecture
The compilation phase is strictly decoupled from the parsing and semantic analysis phases.

RuleForge Source -> Lexer -> Parser -> AST
                                      │
                                      ├──> Interpreter (Reference)
                                      │
                                      └──> Compiler
                                             │
                                             ▼
                                     Compiled Representation
                                             │
                                             ▼
                                          Execute(context)
3. Objectives
Cold Execution: Parse + Compile + Execute.
Warm Execution: Execute pre-compiled rules repeatedly (target scenario for SaaS/host applications).
Benchmarking: Measure throughput (Interpreter vs Compiled) across 1, 10, 100, and 1000 rules.
4. V9 Compiler Boundary (Alpha Phase)
The V9.0.0-alpha Compiler acts as a passthrough to the Interpreter.
It establishes the conformance testing infrastructure before any IL/Expression Trees generation is implemented.
No AST modifications are allowed during compilation.
