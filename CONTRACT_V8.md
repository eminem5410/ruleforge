# RuleForge V8.0 — Action / Intent Model (EMIT) Contract

This document is the normative specification for the V8.0 extension. 
It is additive to the V7 Baseline and MUST NOT alter existing V7 semantics.

## 1. Objective
To allow rules to emit structured intents (declarations of what should happen) without executing side effects. RuleForge decides and declares; the host application executes.

## 2. Syntax
The `THEN` and `ELSE` clauses now accept the `EMIT` action.

```text
<action> ::= ... | EMIT <string_literal> [WITH <context_path>]
Example:


RULE suspicious_login LANGUAGE 2
WHEN customer.risk_score >= 80
THEN EMIT "BLOCK_USER" WITH customer.id
END
3. Lexer & Parser Changes
Lexer: Add keywords EMIT and WITH to the keywords dictionary.
Parser: Extend the ParseAction rule to handle EMIT.
EMIT MUST be followed by a STRING literal (the intent name).
The WITH clause is optional.
If WITH is present, it MUST be followed by a PropertyAccessExpression (e.g., customer.id). Arbitrary expressions are NOT allowed as payloads.
4. AST Representation
A new node EmitActionNode represents this:

IntentName: The string literal (e.g., "BLOCK_USER").
PayloadPath (optional): The AST node representing the property path.
5. Semantic Validation
If WITH <path> is used, the path MUST exist in the context schema.
If the property does not exist, the analyzer MUST throw RF3002 (Unknown context property).
6. Runtime Behavior
The engine evaluates the PayloadPath against the runtime context.
If the property evaluates to NULL in runtime, the payload in the decision is null. This is NOT a runtime error (RF4002 is not thrown for EMIT payloads).
The engine returns a decision containing the resolved intent.
7. V7 Compatibility Boundary
Existing actions (ALLOW, DENY, NO_ACTION, ALERT, APPLY) MUST retain their exact V7 behavior.
EMIT can be combined with other actions in the same action list.
EMIT does not modify the context or the flow of rule evaluation.
