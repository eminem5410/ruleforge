using RuleForge.Core.Lexing;

namespace RuleForge.Core.Syntax;

public abstract record Expression;

public sealed record LiteralExpression(object Value, TokenType Type) : Expression;

public sealed record PropertyExpression(string ObjectName, string PropertyName) : Expression;

public sealed record BinaryExpression(Expression Left, string Operator, Expression Right) : Expression;

public sealed record UnaryExpression(string Operator, Expression Operand) : Expression;

public sealed record NullCheckExpression(Expression Left, bool IsNot) : Expression;

public sealed record FunctionCallExpression(string Name, List<Expression> Arguments) : Expression;

public sealed record ArrayLiteralExpression(List<Expression> Elements) : Expression;

public sealed record ArrayIndexExpression(Expression Array, Expression Index) : Expression;

public sealed record AnyAllExpression(bool IsAll, Expression ArrayExpr, Expression WhereExpr) : Expression;

public sealed record ItExpression() : Expression;

public record ActionNode(string ActionType, string? Value = null, object? Payload = null);

public sealed record EmitActionNode(string IntentName, Expression? PayloadPath) : ActionNode("EMIT", IntentName);

public sealed record SetActionNode(string Path, Expression ValueExpr) : ActionNode("SET", Path);

public sealed record RuleNode(string Name, int LanguageVersion, Expression WhenExpr, List<ActionNode> ThenActions, List<ActionNode> ElseActions);

public sealed record DateLiteralExpression(DateOnly Value) : Expression;