# RuleForge Language Specification
**Version:** 0.1.0
**Status:** Draft

RuleForge is a deterministic, typed, and sandboxed domain-independent rule language. The language is designed to express business decisions independently from application code.

## 1. Goals
- Allow domain experts and developers to define business rules in a readable format.
- Decouple business logic from application source code.
- Ensure deterministic evaluation: given a rule, a context, and a version, the output decision is always identical.
- Provide strict type safety and verbose error reporting before execution.

## 2. Non-Goals
RuleForge V1 is **not** intended to be:
- A general-purpose programming language.
- A scripting language.
- A workflow engine.
- A database query language.
- A Turing-complete language (no loops, no recursion, no dynamic allocation).
- A replacement for C#, Python, or JavaScript.

## 3. Language Philosophy
**The Golden Rule:** A RuleForge rule must *never* directly perform external side effects. Actions like ALERT or APPLY are declarations of intent. The host application decides what to do with them.

## 4. Source File Structure
A source file contains one or more rules. Each rule is defined by the following structure:

RULE <rule_identifier>
WHEN
    <boolean_expression>
THEN
    <action>
[ELSE
    <action>]
END

## 5. Rules
A rule consists of an identifier, a condition (WHEN), and consequences (THEN, ELSE).
- **Identifier:** Must be a string without spaces (e.g., premium_customer_discount).

## 6. Expressions
An expression calculates a value. Expressions can be:
- **Literals:** 65, "active", true
- **Property Access:** customer.age
- **Binary Operations:** customer.age + 1
- **Function Calls:** length(customer.name)

## 7. Operators
- **Comparison:** ==, !=, >, <, >=, <=
- **Logical:** AND, OR, NOT
- **Mathematical:** +, -, *, / (Restricted to numeric types)

## 8. Data Types
V1 supports the following primitive types:
- String
- Integer
- Decimal
- Boolean
- Date (ISO 8601 format: YYYY-MM-DD)
- Null (Special type for absence of value)

## 9. Literals
- **String:** "hello", "Villa Gesell"
- **Integer:** 10, -5, 100000
- **Decimal:** 10.5, 99.99
- **Boolean:** true, false
- **Date:** 2026-09-25

## 10. Context and Property Access
Rules evaluate data provided by the host application through a Context. 
Properties are accessed via dot notation: customer.age, invoice.total.
The available properties and their types must be provided via a Context Schema prior to semantic analysis.

## 11. Functions
V1 includes a minimal standard library:
- **Text:** contains(value, text), starts_with(value, text), ends_with(value, text), length(value)
- **Math:** abs(value), min(a, b), max(a, b)
- **Date:** year(date), month(date), day(date)

*Note: now() and random() are strictly forbidden to maintain determinism. Time must be passed via Context.*

## 12. Conditions
The WHEN block requires a boolean expression. If the expression evaluates to true, the THEN action is returned. If it evaluates to false and an ELSE block exists, the ELSE action is returned.

## 13. Actions
Actions are the output of a rule. They do not execute logic; they return a decision to the host.
- ALLOW
- DENY "Reason string"
- ALERT "Message string"
- APPLY "identifier"
- NO_ACTION

## 14. ELSE
The ELSE block is optional. If omitted and the WHEN condition is false, the rule implicitly returns NO_ACTION.

## 15. Null Semantics
Null checking must be explicit using the IS NULL or IS NOT NULL operators.
Example:
WHEN
    customer.email IS NOT NULL

Comparing directly to null (e.g., customer.email == null) will result in a Semantic Error.

## 16. Type System
RuleForge is strictly typed. Type mismatches are caught during semantic analysis.
Example of an error:
customer.age > "65"
This fails because > expects numeric operands, but received a String. No implicit type coercion is performed.

## 17. Error Model
Errors include a code, message, line, and column.
- **RF1xxx:** Lexical Errors (invalid characters)
- **RF2xxx:** Parse Errors (syntax mistakes)
- **RF3xxx:** Semantic / Type Errors (invalid operations, unknown properties)
- **RF4xxx:** Runtime Errors (evaluation limits reached)
- **RF5xxx:** Security / Resource Limits

*Example Output:*
RF3001 Type Error
Line: 4, Column: 19
Operator '>':
left operand: Integer
right operand: String
Expected: Integer
Received: String

## 18. Determinism
Given:
1. Rule Source
2. Context Schema & Data
3. Language Version

The evaluation will always produce the exact same Decision object.

## 19. Security Constraints
- No filesystem access.
- No network access.
- No dynamic code execution.
- Resource limits: Max AST depth, Max execution time (e.g., 50ms per rule).

## 20. Versioning
Rules can declare their expected language version:
RULE my_rule LANGUAGE 1
...
END

This allows the engine to evolve without breaking older rules.

## 21. Examples

**ERP Context:**
RULE credit_check
WHEN
    customer.debt <= 50000
    AND customer.status == "active"
THEN
    ALLOW
ELSE
    DENY "Credit limit exceeded"
END

**HealthTech Context:**
RULE elderly_patient_review
WHEN
    patient.age >= 65
    AND patient.active == true
THEN
    ALERT "Requires clinical review"
END

## 22. Future Extensions (V2+)
- LET statements for temporary variables.
- Array and Object types.
- DateTime and Duration types.
- Money and Enum types.
- Nested property access (e.g., customer.address.city).
