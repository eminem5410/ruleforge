# RuleForge Language Specification
Version: 7.0.0
Status: Core Stable (Runtime Validated)

## 1. Goals & Philosophy
RuleForge is a deterministic, typed, and sandboxed domain-independent rule language.
The Golden Rule: A RuleForge rule must never directly perform external side effects.

## 2. Type System & NULL Semantics
- Strict typing. No implicit coercion.
- Missing properties in runtime context are evaluated as NULL.
- RuleForge does NOT use 3-valued logic (like SQL's UNKNOWN). 
- NULL is NOT a comparable value. Any arithmetic or comparison operation (==, !=, >, <, +, -) against NULL raises RF4002 Runtime Type Error.
- NULL can ONLY be used with `IS NULL` or `IS NOT NULL` operators.
- Decimal type uses exact arithmetic (Python's decimal.Decimal) to prevent floating-point precision issues.

## 3. Versioning
- `language_version`: Declared explicitly in rule syntax (e.g., `LANGUAGE 1`).
- `rule_version`: RuleForge V1 syntax does not define a rule-version field. The runtime reports `rule_version = 1` as the implicit rule definition version.

## 4. Error Model
- RF1xxx: Lexical Errors
- RF2xxx: Parse Errors
- RF3xxx: Semantic/Type Errors (Static Analysis)
- RF4xxx: Runtime Errors
  - RF4001: Runtime Error (e.g., Division by zero, unexpected internal failure)
  - RF4002: Runtime Type Error (e.g., NULL arithmetic, incompatible operations)
  - RF4003: Invalid Runtime Context (Context data structure or types do not match Schema)
- RF5xxx: Security / Resource Limits

## 14. V7.0.0 Language Extensions (Arrays)

### 14.1 EBNF Additions
factor          = literal | property_access | function_call | "(" expression ")" | array_literal ;
array_literal   = "[" [ expression { "," expression } ] "]" ;
property_access = identifier "." identifier | identifier "." identifier "[" integer "]" ;
function_call   = identifier "(" [ expression { "," expression } ] ")" ;

Note: Array indexing only supports integer literals in V7. CONTAINS is added to the standard library.

### 14.2 Type Matrix Additions
Left = Array<T> | Op = CONTAINS | Right = T | Result = Boolean
Left = Array<T> | Op = LENGTH | Right = (none) | Result = Integer

### 14.3 Error Codes for Arrays
- RF3003 Semantic Error: Heterogeneous array literal.
- RF4002 Runtime Type Error: Indexing a NULL array, Out of bounds index, or calling LENGTH/CONTAINS on NULL.

## 15. Backward Compatibility
Language Version 2 is backward-compatible with Language Version 1. 
All valid V1 programs remain valid under V2 unless explicitly deprecated. 
The Conformance Suite vectors for V1 (RF-CONF-001 to 007) are considered valid for V2.
