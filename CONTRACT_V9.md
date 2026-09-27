# RuleForge V9.0 — Compilation / Optimization Contract (Stable)

This document is the normative specification for the V9.0 stable release. 
V9 introduces a compilation phase that optimizes execution throughput, strictly preserving V7/V8 semantics.

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
3. Supported Compiled Nodes (100% Coverage)
The V9 compiler natively compiles the following AST nodes. Unsupported nodes (e.g., future V10 features) safely fall back to the Interpreter.

Literals (Integer, Decimal, String, Boolean, Date)
PropertyAccess (Context variables)
Binary Operations (+, -, *, /, ==, !=, >, <, >=, <=, AND, OR)
Unary Operations (NOT)
Null Checks (IS NULL, IS NOT NULL)
Function Calls (LENGTH, CONTAINS, DATE_ADD, DATE_DIFF, EXTRACT)
Array Literal & Array Indexing (with bounds and null checking)
Action Resolution (ALLOW, DENY, NO_ACTION, EMIT)
4. Sandbox Security (Python)
The Python compiler generates restricted Python expressions evaluated via eval().
The global namespace is strictly controlled:
{"__builtins__": {}, "_safe_get": ..., "Decimal": ..., "date": ..., "timedelta": ..., "_get_date": ..., "_safe_index": ...}
No access to filesystem, imports, or environment is permitted.

5. Determinism
The core engine (Lexer, Parser, SemanticAnalyzer, Evaluator, Compiler) contains NO non-deterministic functions.
same rule + same language version + same context = same Decision.

6. Performance (Audited)
Benchmarked at 1,000,000 iterations of a mixed rule (Arithmetic + String + Function):

Interpreter: ~1.03M ops/sec
Compiled: ~3.59M ops/sec
Speedup: ~3.4x
