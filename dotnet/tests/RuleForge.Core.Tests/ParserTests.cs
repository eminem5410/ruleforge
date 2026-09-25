using Xunit;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parser;
using RuleForge.Core.Syntax;

namespace RuleForge.Core.Tests;

public class ParserTests
{
    private List<RuleNode> ParseCode(string source)
    {
        var tokens = new Lexer(source).Tokenize();
        return new Parser(tokens).Parse();
    }

    [Fact]
    public void PARSE_001_BasicRule()
    {
        var ast = ParseCode("RULE test LANGUAGE 1 WHEN active == true THEN ALLOW END");
        var rule = ast[0];
        Assert.Equal("test", rule.Name);
        Assert.Equal(1, rule.LanguageVersion);
        Assert.IsType<BinaryExpression>(rule.WhenExpr);
        Assert.Equal("ALLOW", rule.ThenActions[0].ActionType);
    }

    [Fact]
    public void PARSE_002_MultipleActions()
    {
        var ast = ParseCode("RULE r LANGUAGE 1 WHEN true THEN DENY \"No\" ALERT \"Check\" END");
        Assert.Equal(2, ast[0].ThenActions.Count);
        Assert.Equal("DENY", ast[0].ThenActions[0].ActionType);
        Assert.Equal("No", ast[0].ThenActions[0].Value);
    }

    [Fact]
    public void PARSE_003_PrecedenceAndBeforeOr()
    {
        var ast = ParseCode("RULE r LANGUAGE 1 WHEN a OR b AND c THEN ALLOW END");
        var when = ast[0].WhenExpr;
        Assert.IsType<BinaryExpression>(when);
        Assert.Equal("OR", ((BinaryExpression)when).Operator);
        Assert.IsType<BinaryExpression>(((BinaryExpression)when).Right);
        Assert.Equal("AND", ((BinaryExpression)((BinaryExpression)when).Right).Operator);
    }

    [Fact]
    public void PARSE_004_UnaryNot()
    {
        var ast = ParseCode("RULE r LANGUAGE 1 WHEN NOT active THEN ALLOW END");
        Assert.IsType<UnaryExpression>(ast[0].WhenExpr);
    }

    [Fact]
    public void PARSE_005_IsNotNullNull()
    {
        var ast = ParseCode("RULE r LANGUAGE 1 WHEN email IS NOT NULL THEN ALLOW END");
        Assert.IsType<NullCheckExpression>(ast[0].WhenExpr);
        Assert.True(((NullCheckExpression)ast[0].WhenExpr).IsNot);
    }

    [Fact]
    public void PARSE_ERR_001_MissingEnd()
    {
        var ex = Assert.Throws<ParserException>(() => ParseCode("RULE r LANGUAGE 1 WHEN true THEN ALLOW"));
        Assert.Equal("RF2002", ex.Code);
    }
}
