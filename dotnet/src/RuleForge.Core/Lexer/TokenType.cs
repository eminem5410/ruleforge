namespace RuleForge.Core.Lexing;

public enum TokenType
{
    // Keywords
    RULE, LANGUAGE, WHEN, THEN, ELSE, END,
    ALLOW, DENY, NO_ACTION, ALERT, APPLY,
    AND, OR, NOT, IS, NULL,
    
    // Literals
    IDENTIFIER, INTEGER, DECIMAL, STRING, BOOLEAN, DATE,
    
    // Operators
    EQ, NEQ, GT, LT, GTE, LTE,
    PLUS, MINUS, MULTIPLY, DIVIDE,
    
    // Symbols
    LPAREN, RPAREN, DOT, COMMA,
    
    // Control
    EOF
}
