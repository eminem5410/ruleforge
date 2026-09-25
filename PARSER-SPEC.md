# RuleForge Parser Specification

The Parser is responsible for converting a stream of Tokens into an Abstract Syntax Tree (AST). It does not evaluate or check semantic validity (types, context existence); it only enforces syntax rules.

## 1. AST Node Model
- `RuleNode`: Contains rule_name, language_version, when_expr, then_actions, else_actions.
- `ActionNode`: Contains action_type (ALLOW, DENY, etc.) and optional value (string).
- `BinaryOpNode`: Contains left, op, right. Used for logical (AND/OR) and arithmetic/comparison operators.
- `NullCheckNode`: Contains left, is_not. Used for IS NULL / IS NOT NULL.
- `LiteralNode`: Contains value and type.
- `PropertyAccessNode`: Contains obj, prop.
- `FunctionCallNode`: Contains name, args (list of nodes).

## 2. Parser Architecture
- Recursive Descent Parser.
- Enforces Operator Precedence (OR < AND < NOT < Comparison < Add/Sub < Mul/Div < Parens).
- Does NOT verify if a property exists in Context (Semantic Analyzer's job).
- Does NOT verify if a function is built-in (Semantic Analyzer's job).

## 3. Error Model
- RF2001 Parse Error (General syntax mistake)
- RF2002 Unexpected Token (Expected X, got Y)
- RF2003 Unexpected EOF (Missing tokens to complete rule)
- RF2004 Invalid Expression (Malformed arithmetic or logical expression)
- RF2005 Invalid Action (Malformed action block)
