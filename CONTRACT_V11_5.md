# RuleForge V11.5 — Compiler Performance & Sequential Semantics

## Status
**Frozen — V11.5.0 / V11.6.0**

## 1. Scope
V11.5 eliminates quadratic compiler pipeline evaluation.
V11.6 refactors shared compiler logic.
Neither introduces new DSL capabilities.

## 2. execute_single()
RuleForgeCompiler.execute_single(rule, context) evaluates one rule
without re-evaluating the complete rule set.

The engine calls execute_single per rule, achieving O(N) pipeline
scaling instead of the previous O(N^2).

## 3. Sequential SET Semantics
RuleForge evaluates rules sequentially. SET from rule N is visible
to rule N+1. No rule observes SETs from future rules.

This behavior is frozen with 12 regression tests and 1500
property-based examples covering:
- basic SET visibility
- non-matching rules
- chained SET operations
- prevention of future-state leakage
- multiple SET operations
- SET followed by DENY
- generated SET chains (interpreter == compiler)

## 4. Internal Architecture
_execute_compiled_rule(): shared execution path for both
execute() and execute_single().

_resolve_actions(): shared action resolution (SET/EMIT/ALLOW/DENY).

execute() can optionally reuse an Evaluator across rules.
execute_single() creates a new Evaluator per call.

## 5. Fallback
Non-compilable conditions (ANY/ALL/FILTER/MAP) fall back to
Evaluator.eval_rule(). This preserves semantic equivalence.

## 6. Performance
Compiler eval-only: ~131K ops/s (simple), ~125K (complex)
Pipeline overhead: ~90% of total time for simple rules
Trace overhead: ~20-30%
Array scaling: O(N)

## 7. Golden Rule
The compiler optimizes execution without changing observable
semantics. The Evaluator remains the authority.
