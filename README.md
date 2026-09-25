# ⚙️ RuleForge

A deterministic, typed, and sandboxed domain-independent rule engine. RuleForge is designed to express business decisions independently from application code.

## Philosophy
RuleForge is not a general-purpose programming language. It is a declarative DSL designed with four pillars in mind:
- **Deterministic**: Given a rule, a context, and a version, the output decision is always identical.
- **Typed**: Strict type system. Type mismatches are caught before execution.
- **Sandboxed**: No external side effects. Actions like ALLOW or DENY are declarations of intent. The host application decides what to do with them.
- **Auditable**: Includes an explain mode to trace exactly why a decision was made.

## Architecture
- **Lexer**: Tokenizes the source code.
- **Parser**: Builds an Abstract Syntax Tree (AST) using recursive descent.
- **Semantic Analyzer**: Validates types and context properties using an external Schema.
- **Evaluator**: Walks the AST and produces a Decision object without side effects.
