# RuleForge Language Contract (V7 Baseline)

This document is the normative specification of the RuleForge language (V7.x). 
In case of ambiguity between implementations (Python, C#, or future runtimes) and documentation, **this contract mandates**.

## 1. Grammar

### Rule Structure
```text
RULE <identifier> LANGUAGE <integer> WHEN <expression> THEN <action_list> [ELSE <action_list>] END
Operators & Precedence
OR
AND
NOT
IS NULL, IS NOT NULL
==, !=, >, <, >=, <=
+, -
*, /
Primary: Literals, Identifiers, Property Access, Array Indexing, Function Calls, (expression)
Literals
Integer: [0-9]+
Decimal: [0-9]+.[0-9]+
String: "..."
Boolean: true, false
Date: DATE "YYYY-MM-DD" (Strict prefix format, no implicit string coercion).
Arrays
Literal: [<expression>, ...]
Indexing: <property>.<property>[<integer_literal>]
Constraints:
Indexing is strictly restricted to context properties.
Indices MUST be single integer literals (e.g., arr[0]). Expressions like arr[1+1] are forbidden.
Chained indexing (e.g., arr[0][1]) is forbidden.
2. Type System
Integer
Decimal
String
Boolean
Date
Array<T>: Homogeneous arrays. Heterogeneous arrays are a semantic error (RF3003). Nested arrays are forbidden.
Null
Context Schema
Rules are evaluated against a strictly typed context schema. Unmatched properties or type mismatches result in semantic errors (RF3002, RF3003).

3. Functions
LENGTH(String) -> Integer
LENGTH(Array<T>) -> Integer
CONTAINS(String, String) -> Boolean
CONTAINS(Array<T>, T) -> Boolean
DATE_ADD(Date, Integer) -> Date (Adds days to a Date)
DATE_DIFF(Date, Date) -> Integer (Calendar days between two Dates: end - start)
EXTRACT(Date, String) -> Integer (Extracts "year", "month", or "day")
Invalid arguments or unknown units (e.g., EXTRACT(date, "century")) result in RF3003.

4. Error Model
Prefix
Layer
Description
RF1xxx	Lexer	Invalid characters, unterminated strings, malformed tokens.
RF2xxx	Parser	Syntax errors, missing tokens, invalid array indexing, invalid dates.
RF3xxx	Semantic	Type mismatches, unknown properties, invalid function arguments.
RF4xxx	Runtime	Division by zero, NULL operand violations, out-of-bounds array access.
RF5xxx	Security	Execution limits (e.g., max steps exceeded).

5. Determinism (Constitutional Clause)
Given the same rule source, language version, context, and adapter contract, RuleForge MUST produce the same decision and declared actions.

Explicitly out of scope for the core engine:

NOW(), CURRENT_DATE(), or any time-dependent function.
RANDOM() or any non-deterministic function.
HTTP calls, filesystem access, database writes, or network I/O.
Environment-dependent behavior.
6. Cross-Language Invariant
Python and C# implementations MUST produce equivalent observable results for every canonical conformance vector. This is enforced automatically by the Cross-Language Runner in CI.

7. V8 Boundary & Compatibility Guarantee
V8 Boundary
V8 extensions MUST NOT alter the meaning of valid V7 rules. Extensions (such as EMIT) are additive and must coexist with V7 actions (ALLOW, DENY, ALERT, APPLY, NO_ACTION).

Compatibility Guarantee
Any rule valid under V7.x MUST preserve its observable decision semantics under future RuleForge versions unless a new language version explicitly declares a breaking change. Internal optimizations (e.g., AST compilation) MUST NOT alter observable outcomes.
