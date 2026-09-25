using Xunit;
using RuleForge.Core.Lexing;

namespace RuleForge.Core.Tests;

public class LexerTests
{
    private List<Token> Tokenize(string source) => new Lexer(source).Tokenize();

    [Fact]
    public void LEX_001_KeywordAndIdentifier()
    {
        var tokens = Tokenize("RULE customer_check");
        Assert.Equal(TokenType.RULE, tokens[0].Type);
        Assert.Equal(TokenType.IDENTIFIER, tokens[1].Type);
        Assert.Equal("customer_check", tokens[1].Value);
    }

    [Fact]
    public void LEX_002_PropertyAccessAndOperators()
    {
        var tokens = Tokenize("customer.age >= 18");
        Assert.Equal(TokenType.IDENTIFIER, tokens[0].Type);
        Assert.Equal(TokenType.DOT, tokens[1].Type);
        Assert.Equal(TokenType.IDENTIFIER, tokens[2].Type);
        Assert.Equal(TokenType.GTE, tokens[3].Type);
        Assert.Equal(TokenType.INTEGER, tokens[4].Type);
    }

    [Fact]
    public void LEX_003_StringLiteral()
    {
        var tokens = Tokenize("\"Credit limit exceeded\"");
        Assert.Equal(TokenType.STRING, tokens[0].Type);
        Assert.Equal("Credit limit exceeded", tokens[0].Value);
    }

    [Fact]
    public void LEX_004_DateLiteral()
    {
        var tokens = Tokenize("1990-05-20");
        Assert.Equal(TokenType.DATE, tokens[0].Type);
        Assert.Equal("1990-05-20", tokens[0].Value);
    }

    [Fact]
    public void LEX_ERR_001_InvalidCharacter()
    {
        var ex = Assert.Throws<LexerException>(() => Tokenize("customer @ age"));
        Assert.Equal("RF1001", ex.Code);
        Assert.Contains("Unexpected character '@'", ex.Message);
    }
}
