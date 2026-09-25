namespace RuleForge.Core.Lexing;

public record Token(TokenType Type, string Value, int Line, int Column);
