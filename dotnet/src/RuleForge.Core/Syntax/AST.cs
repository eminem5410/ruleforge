namespace RuleForge.Core.Syntax;

public abstract record Expression;

public sealed record LiteralExpression(object Value, TokenType Type) : Expression;

public sealed record PropertyExpression(string ObjectName, string PropertyName) : Expression;

public sealed record BinaryExpression(Expression Left, string Operator, Expression Right) : Expression;

public sealed record UnaryExpression(string Operator, Expression Operand) : Expression;

public sealed record NullCheckExpression(Expression Left, bool IsNot) : Expression;

public sealed record ActionNode(string ActionType, string? Value = null);

public sealed record RuleNode(string Name, int LanguageVersion, Expression WhenExpr, List<ActionNode> ThenActions, List<ActionNode> ElseActions);
