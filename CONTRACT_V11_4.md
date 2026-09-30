# RuleForge V11.4 — Runtime Safety & Determinism

## Status

**Frozen — V11.4.0**

This document defines runtime safety limits and their cross-runtime
contract. It is not frozen until all four pillars (Execution Limits,
Property-Based Testing, Fuzzing, Benchmarks) are complete.

---

## 1. Scope

V11.4 does not introduce new DSL syntax.

It hardens the runtime against pathological rules and ensures
bounded, deterministic execution.

---

## 2. Security limits

All limits are defined as named constants in both runtimes.

| Limit | Python constant | C# constant | Value |
|---|---|---|---|
| AST depth | MAX_AST_DEPTH | MaxAstDepth | 50 |
| AST node count | MAX_AST_NODES | MaxAstNodes | 500 |
| Execution steps | MAX_EXECUTION_STEPS | MaxExecutionSteps | 10000 |

Values MUST be identical between Python and C#.

---

## 3. Error codes

| Code | Condition | Phase |
|---|---|---|
| RF5001 | AST depth exceeds maximum | Semantic analysis |
| RF5002 | AST node count exceeds maximum | Semantic analysis |
| RF5003 | Execution step count exceeds maximum | Evaluation |
| RF5004 | Unmapped AST node type during trace generation | Evaluation (trace only) |

RF5001 and RF5002 are enforced by the Semantic Analyzer before evaluation.
RF5003 is enforced by the Evaluator during evaluation.
RF5004 is enforced by the trace builder during evaluation.

---

## 4. AST traversal for limits

The Semantic Analyzer MUST traverse ALL expression types for depth
and node-count checking.

Traversed node types:

- BinaryExpression / BinaryOpNode (left, right)
- UnaryExpression / UnaryOpNode (operand)
- NullCheckExpression / NullCheckNode (left)
- FunctionCallExpression / FunctionCallNode (arguments)
- ArrayLiteralExpression / ArrayLiteralNode (elements)
- ArrayIndexExpression / ArrayIndexNode (array, index)
- AnyAllExpression / AnyAllNode (array_expr, where_expr)
- FilterMapExpression / FilterMapNode (array_expr, sub_expr)

AnyAll and FilterMap sub-expressions MUST be traversed.

V11.4 fix: Python count accumulation was broken (pass-by-value).
Fixed by returning (max_depth, count) from recursive calls,
matching C#'s ref-based accumulation.

---

## 5. Count accumulation

Python: check_ast_limits returns (max_depth, count) and each
branch accumulates from recursive calls.

C#: CheckAstLimits uses ref int count, accumulating across
all recursive calls including siblings.

Both runtimes MUST produce the same count for the same AST.

---

## 6. Bounded operations

ANY, ALL, FILTER, and MAP iterate over arrays.

The execution step limit (RF5003) bounds the total number
of evaluation steps, including iterations.

MAX_EXECUTION_STEPS is scoped to a single rule evaluation.
The counter MUST reset for each independent evaluation.

The counter is monotonically increasing during one evaluation.
When the next step would exceed the limit, evaluation MUST terminate
with RF5003.

V11.4 does not introduce a separate collection-size limit.
A future RF5005 may be defined if profiling demonstrates
that large arrays cause unacceptable latency before RF5003
triggers.

---

## 7. Test coverage

V11.4 requires tests for:

| Test | Python | C# |
|---|---|---|
| RF5001 depth (linear chain) | YES | YES |
| RF5001 depth (ANY WHERE) | YES | YES |
| RF5001 depth (ALL WHERE) | YES | YES |
| RF5001 depth (FILTER WHERE) | YES | YES |
| RF5001 depth (MAP USING) | YES | YES |
| RF5002 node count (array literal) | YES | YES |
| RF5002 node count (ANY array) | YES | YES |
| RF5002 node count (ALL array) | YES | YES |
| RF5002 node count (FILTER array) | YES | YES |
| RF5002 node count (MAP array) | YES | YES |
| RF5003 execution steps | YES | YES (conformance) |

All tests MUST pass in both runtimes with identical error codes.

---

## 8. Determinism guarantee

Given the same rule source and context:

- The same decision is produced regardless of trace mode.
- The same error code is produced when limits are exceeded.
- The same limit MUST trigger for equivalent ASTs in both runtimes.
  Verified by 2100 property-based cross-language examples.

---

## 9. Pending pillars

| Pillar | Status |
|---|---|
| Execution Limits | Complete |
| Property-Based Testing | Complete (2100 examples) |
| Fuzzing | Complete (14600 examples) |
| Benchmarks | Complete |

V11.4 is not released until all pillars are complete and frozen.

---

## 10. Benchmarks

V11.4 includes comprehensive benchmarks measuring:

- Full pipeline latency (Lexer -> Parser -> Semantic -> Engine)
- Evaluation-only throughput (pre-built AST)
- Interpreter vs Compiler comparison
- Multi-rule scaling (1/10/50/100/250 rules)
- Array scaling (10/50/100/200/400 elements)
- Trace overhead (trace=False vs trace=True)

Key findings:

- Pipeline overhead is ~90% of total time for simple rules
- Compiler eval-only is FASTER than interpreter for simple/complex
- Trace overhead is ~20-30% (acceptable for observability)
- Array operations scale linearly O(N)
- MAX_AST_NODES=500 correctly limits array sizes

### Known Performance Limitation

The current compiler integration in RuleEngine.evaluate() invokes
compiler.execute() once per rule. Since compiler.execute() evaluates
the complete rule set, the full-pipeline compiler path exhibits
O(N^2) scaling with the number of rules.

This does NOT affect semantic correctness.

The compiler's evaluation-only path remains approximately O(N).

Optimization is intentionally deferred to V11.5 because SET actions
may mutate the working context between rules. Any optimization must
preserve sequential rule semantics.

## 11. Golden rule

Limits are safety guards, not semantic features.

A rule that exceeds a limit is rejected with a defined error code.
The runtime does not hang, crash, or produce undefined behavior.

The Evaluator remains the authority.
Limits observe and bound; they do not alter semantics.
