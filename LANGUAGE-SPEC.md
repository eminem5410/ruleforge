# RuleForge Language Specification
**Version:** 0.2.0
**Status:** Draft - Architecture Frozen (No code changes until spec is final)

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
- A Turing-complete language (no loops, no recursion, no dynamic allocation).

## 3. Language Philosophy
**The Golden Rule:** A RuleForge rule must *never* directly perform external side effects. Actions like ALERT or APPLY are declarations of intent. The host application decides what to do with them.

## 4. Formal Grammar (EBNF)
This is the definitive syntax contract for RuleForge V1.

```ebnf
rule            = "RULE" identifier "LANGUAGE" integer
                  "WHEN" expression
                  "THEN" action_list
                  [ "ELSE" action_list ]
                  "END" ;

action_list     = action { action } ;

action          = "ALLOW"
                | "NO_ACTION"
                | ("DENY" | "ALERT" | "APPLY") string ;

expression      = logical_or ;

logical_or      = logical_and { "OR" logical_and } ;

logical_and     = logical_not { "AND" logical_not } ;

logical_not     = "NOT" logical_not
                | comparison ;

comparison      = arithmetic [ comp_operator arithmetic ] ;

comp_operator   = "==" | "!=" | ">" | "<" | ">=" | "<=" | "IS" [ "NOT" ] "NULL" ;

arithmetic      = term { ("+" | "-") term } ;

term            = factor { ("*" | "/") factor } ;

factor          = literal
                | property_access
                | function_call
                | "(" expression ")" ;

property_access = identifier "." identifier ;

function_call   = identifier "(" [ expression { "," expression } ] ")" ;
Operator Precedence (Lowest to Highest)
OR
AND
NOT
Comparison (==, !=, >, <, >=, <=, IS NULL)
Addition/Subtraction (+, -)
Multiplication/Division (*, /)
Parentheses / Function Calls
5. Data Types
String
Integer
Decimal
Boolean
Date (ISO 8601 format: YYYY-MM-DD)
Null (Special type for absence of value)
6. Type Compatibility Matrix
Strict typing. No implicit coercion.

Left
Op
Right
Result
Notes
Int	+/-	Int	Int	Standard arithmetic
Int	+/-	Dec	Dec	Promotion to Decimal
Dec	+/-	Dec	Dec	Standard arithmetic
Int	*	Int	Int	Standard arithmetic
Int	/	Int	Dec	Division always yields Decimal
Int	/	Dec	Dec	Standard arithmetic
Str	==	Str	Boolean	String equality
Date	<	Date	Boolean	Chronological comparison
Date	==	Date	Boolean	Date equality
Any	IS N	Any	Boolean	Null check

Note: Date arithmetic (e.g., Date + Integer) is explicitly forbidden in V1 due to lack of Duration type.

7. Context and Property Access
Rules evaluate data provided by the host application through a Context.
Properties are accessed via dot notation: customer.age, invoice.total.
The available properties and their types must be provided via a Context Schema prior to semantic analysis.

8. Functions (Standard Library V1)
Strict signatures. No function overloading in V1.

length(String) -> Integer
contains(String, String) -> Boolean
starts_with(String, String) -> Boolean
ends_with(String, String) -> Boolean
abs(Integer) -> Integer
abs(Decimal) -> Decimal (Exception to overloading rule for practical math)
Note: now() and random() are strictly forbidden to maintain determinism.

9. Actions
Actions are the output of a rule. They do not execute logic; they return a decision to the host.
Multiple actions are allowed in a single THEN or ELSE block.

ALLOW
DENY "Reason string"
ALERT "Message string"
APPLY "identifier" (Declares intent to apply a named external effect/discount)
NO_ACTION
10. Decision Model
The output of a rule evaluation is a structured Decision object.
{
  "rule_id": "credit_check",
  "rule_version": 1,
  "matched": true,
  "actions": [
    { "type": "APPLY", "identifier": "senior_discount" },
    { "type": "ALERT", "message": "Manual review required" }
  ],
  "trace": [ ... ] // Optional, populated only in explain mode
}
11. Error Model
RF1xxx: Lexical Errors (invalid characters)
RF2xxx: Parse Errors (syntax mistakes, unexpected tokens)
RF3xxx: Semantic / Type Errors (invalid operations, unknown properties)
RF4xxx: Runtime Errors (evaluation limits reached)
RF5xxx: Security / Resource Limits
12. Security Constraints & Resource Limits
No filesystem access. No network access. No dynamic code execution.
Max AST depth: 50 nodes.
Max execution time: 50ms per rule.
13. Examples
ERP Context with Multiple Actions:
RULE credit_check
LANGUAGE 1
WHEN
    customer.debt <= 50000
    AND customer.status == "active"
THEN
    ALLOW
    APPLY "standard_credit_line"
ELSE
    DENY "Credit limit exceeded"
    ALERT "Manual review required"
END
