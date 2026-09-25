# RuleForge Language Specification
Version: 1.0.2
Status: Core Stable (Runtime Hardened)

## 1. Goals & Philosophy
RuleForge is a deterministic, typed, and sandboxed domain-independent rule language.
The Golden Rule: A RuleForge rule must never directly perform external side effects.

## 2. Type System & NULL Semantics
- Strict typing. No implicit coercion.
- Missing properties in runtime context are evaluated as NULL.
- NULL can ONLY be used with `IS NULL` or `IS NOT NULL` operators.
- Any arithmetic or comparison operation against NULL raises RF4002 Runtime Type Error.
- Decimal type uses exact arithmetic (Python's decimal.Decimal) to prevent floating-point precision issues.

## 3. Versioning
- `language_version`: Declared explicitly in rule syntax (e.g., `LANGUAGE 1`).
- `rule_version`: RuleForge V1 syntax does not define a rule-version field. The runtime reports `rule_version = 1` as the implicit rule definition version.

## 4. Error Model
- RF1xxx: Lexical Errors
- RF2xxx: Parse Errors
- RF3xxx: Semantic/Type Errors (Static Analysis)
- RF4xxx: Runtime Errors (e.g., Division by zero, Invalid context data, Native exceptions)
- RF5xxx: Security / Resource Limits
