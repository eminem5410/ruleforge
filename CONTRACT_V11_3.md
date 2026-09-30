# RuleForge V11.3 — Trace Contract

## Status

**Frozen contract — V11.3**

This document defines the observable trace behavior shared by the
Python and C# RuleForge runtimes.

V11.3 does not introduce new DSL capabilities.

---

## 1. Trace is observability, not semantics

Evaluation semantics MUST NOT depend on whether tracing is enabled.

Given the same rule and context:

```text
trace=false
trace=true
MUST produce the same rule decisions and semantic evaluation results.

Tracing exists exclusively for observability, diagnostics, debugging,
testing and tooling.

2. trace=False isolation

When tracing is disabled:

trace=false

the runtime MUST NOT expose an EvaluationTrace.

The observable result MUST contain no evaluation trace structure.

The runtime MUST NOT require trace data for normal rule evaluation.

trace=false is the default execution mode.

3. trace=True

When tracing is enabled:

trace=true

an EvaluationTrace is generated for every evaluated rule.

The trace represents the evaluated expression tree.

Trace generation MUST NOT alter evaluation semantics.

4. Trace node contract

A normal trace node contains:

NodeType
Operator? 
Value
Type
Children[]
ShortCircuited
ErrorCode?
ErrorMessage?

Optional fields are omitted when not applicable.

Value MUST represent the observable result of the node.

Type MUST represent the RuleForge runtime type.

5. Stable node types

The following node mappings are part of the V11.3 contract:

AST concept	Trace NodeType
Binary expression	BinaryExpression
Unary expression	UnaryExpression
Null check	NullCheck
Literal	Literal
Property access	PropertyExpression
Function call	FunctionCall
Array literal	ArrayLiteral
Array index	ArrayIndex
Date literal	DateLiteral
ANY / ALL	AnyAll
FILTER / MAP	FilterMap

Runtime-specific internal AST names MUST NOT leak into the
cross-runtime trace contract.

6. Short-circuit evaluation

Short-circuit operators MUST preserve the fact that an expression
was not evaluated.

This applies to:

AND
OR
ANY
ALL

An unevaluated subtree is represented by a phantom trace node:

ShortCircuited = true
Value = null
Type = Null
Children = []

The descendants of a short-circuited subtree MUST NOT be evaluated
or traced.

7. Binding is not an artificial AST node

Bindings introduced by constructs such as:

ANY ... WHERE ...
ALL ... WHERE ...
FILTER ... WHERE ...
MAP ... WHERE ...

represent evaluation context.

They MUST NOT be introduced as artificial trace nodes unless a
future contract explicitly defines such a node.

8. Error capture

When evaluation fails while tracing is enabled, the trace MUST
identify the node where the error occurred.

The failing node MUST contain:

ErrorCode
ErrorMessage
Value = null

The failing node MUST preserve its semantic node type.

For binary operators, the failing node MUST preserve its operator.

Example:

customer.age / 0 > 1

If division by zero occurs, the trace identifies the failing /
node rather than replacing the error with a synthetic root-level
trace.

Error propagation semantics remain unchanged.

9. Decimal serialization

Decimal values MUST be serialized as exact decimal strings.

Example:

1.234567890123456789

MUST remain:

"1.234567890123456789"

It MUST NOT be converted through IEEE-754 floating-point
representation for trace serialization.

Therefore:

Python Decimal -> string
C# decimal   -> invariant string

The change applies to trace serialization only.

It does NOT change Decimal evaluation semantics.

10. Dates

Date values are serialized using ISO-8601 date representation:

YYYY-MM-DD

Example:

2026-09-29
11. Cross-runtime conformance

Python and C# implementations MUST produce semantically equivalent
trace structures for the same rule and equivalent context.

The V11.3 conformance suite contains 16 canonical vectors.

The conformance vectors cover:

literals
property access
binary expressions
unary expressions
null checks
short-circuit OR
short-circuit AND
ANY
ALL
FILTER
MAP
errors
dates
decimals
decimal precision preservation

Changes to trace behavior MUST update the conformance suite and
this contract together.

12. Compiler interaction

The compiler is not required to instrument the AST for V11.3 tracing.

When deep tracing is requested, the interpreted evaluator may be used
to produce the required trace.

The observable result MUST remain semantically equivalent.

13. No external side effects

Tracing MUST NOT introduce external side effects.

Trace generation is observational only.

The RuleForge Golden Rule remains:

Actions declare intent. Rules never perform external side effects.

14. Backward compatibility

V11.3 does not introduce new DSL syntax.

Existing valid rules MUST retain their evaluation semantics.

The V11.3 changes concern:

trace correctness
trace conformance
error observability
Decimal trace serialization
trace isolation
15. Required V11.3 gates

A V11.3 release requires all of the following:

Python tests              PASS
C# Core tests             PASS
C# API tests              PASS
Build                     0 warnings / 0 errors
Trace conformance         PASS
Decimal precision tests   PASS
Error trace tests         PASS
trace=False tests         PASS
git diff --check          PASS

No V11.3 release is considered complete while any gate fails.
