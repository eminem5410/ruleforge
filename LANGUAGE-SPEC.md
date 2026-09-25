# RuleForge Language Specification
Version: 0.4.0
Status: Semantic Contract Frozen

RuleForge is a deterministic, typed, and sandboxed domain-independent rule language.

## 1. Goals & 2. Non-Goals
Declarative DSL, strictly typed, no loops/recursion, not Turing-complete.

## 3. Language Philosophy
The Golden Rule: A RuleForge rule must never directly perform external side effects. Actions are declarations of intent.

## 4. Formal Grammar (EBNF)
rule            = "RULE" identifier "LANGUAGE" integer "WHEN" expression "THEN" action_list [ "ELSE" action_list ] "END" ;
action_list     = action { action } ;
action          = "ALLOW" | "NO_ACTION" | ("DENY" | "ALERT" | "APPLY") string ;
expression      = logical_or ;
logical_or      = logical_and { "OR" logical_and } ;
logical_and     = logical_not { "AND" logical_not } ;
logical_not     = "NOT" logical_not | comparison ;
comparison      = arithmetic [ comp_operator arithmetic ] ;
comp_operator   = "==" | "!=" | ">" | "<" | ">=" | "<=" | "IS" [ "NOT" ] "NULL" ;
arithmetic      = term { ("+" | "-") term } ;
term            = factor { ("*" | "/") factor } ;
factor          = literal | property_access | function_call | "(" expression ")" ;
property_access = identifier "." identifier ;
function_call   = identifier "(" [ expression { "," expression } ] ")" ;
literal         = string | integer | decimal | boolean | date ;
boolean         = "true" | "false" ;

### Operator Precedence (Lowest to Highest)
1. OR
2. AND
3. NOT
4. Comparison (==, !=, >, <, >=, <=, IS NULL)
5. Addition/Subtraction (+, -)
6. Multiplication/Division (*, /)
7. Parentheses / Function Calls

## 5. Data Types
String, Integer, Decimal, Boolean, Date (ISO 8601). Null is NOT a literal value, only used via IS NULL operator.

## 6. Type Compatibility Matrix
Strict typing. No implicit coercion.
Int +/- Int = Int | Int +/- Dec = Dec | Dec +/- Dec = Dec
Int * Int = Int | Int / Int = Dec | Int / Dec = Dec
Str == Str = Boolean | Date == Date = Boolean | Date < Date = Boolean
Any IS NULL = Boolean | Any IS NOT NULL = Boolean
Date arithmetic forbidden in V1.

## 7. Context and Property Access
Dot notation: customer.age. V1 supports exactly one level of property access.

## 8. Functions (Standard Library V1)
- length(String) -> Integer
- contains(String, String) -> Boolean
- starts_with(String, String) -> Boolean
- ends_with(String, String) -> Boolean
- abs(Integer) -> Integer
- abs(Decimal) -> Decimal
(abs is the only built-in function with type-dependent behavior in V1).
now() and random() are strictly forbidden.

## 9. Actions & Semantic Rules
Actions are the output of a rule. Multiple actions allowed in THEN/ELSE.
Terminal Decisions: ALLOW, DENY, NO_ACTION.
Side-Effect Intents: ALERT, APPLY.
A block can have at most ONE terminal decision.
NO_ACTION must be the only action in its block.

## 10. Decision Model
Returns structured JSON. Includes rule_version (metadata) and language_version (from LANGUAGE).

{
  "rule_id": "credit_check",
  "rule_version": 7,
  "language_version": 1,
  "matched": true,
  "actions": [],
  "trace": []
}

## 11. Error Model
RF1xxx Lexical, RF2xxx Parse, RF3xxx Semantic/Type, RF4xxx Runtime (e.g., Division by Zero), RF5xxx Security.

## 12. Security Constraints & Resource Limits
No fs, net, dynamic code. Max AST depth: 50 levels. Max AST nodes: 500. Max execution time: 50ms.
