using Xunit;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Syntax;
using System.Collections.Generic;

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
    public void PARSE_006_FunctionCall()
    {
        var ast = ParseCode("RULE r LANGUAGE 1 WHEN contains(customer.name, \"Pablo\") THEN ALLOW END");
        Assert.IsType<FunctionCallExpression>(ast[0].WhenExpr);
        Assert.Equal("contains", ((FunctionCallExpression)ast[0].WhenExpr).Name);
        Assert.Equal(2, ((FunctionCallExpression)ast[0].WhenExpr).Arguments.Count);
    }

    [Fact]
    public void PARSE_ERR_001_MissingEnd()
    {
        var ex = Assert.Throws<ParserException>(() => ParseCode("RULE r LANGUAGE 1 WHEN true THEN ALLOW"));
        Assert.Equal("RF2002", ex.Code);
    }

    // --- V7 Array Tests ---

    [Fact]
    public void PARSE_007_ArrayLiteral()
    {
        var ast = ParseCode("RULE r LANGUAGE 2 WHEN LENGTH([1, 2, 3]) == 3 THEN ALLOW END");
        var when = ast[0].WhenExpr;
        Assert.IsType<BinaryExpression>(when);
        var funcCall = ((BinaryExpression)when).Left as FunctionCallExpression;
        Assert.NotNull(funcCall);
        Assert.Equal("LENGTH", funcCall.Name);
        var arrLit = funcCall.Arguments[0] as ArrayLiteralExpression;
        Assert.NotNull(arrLit);
        Assert.Equal(3, arrLit.Elements.Count);
    }

    [Fact]
    public void PARSE_008_ArrayIndexing()
    {
        var ast = ParseCode("RULE r LANGUAGE 2 WHEN customer.tags[0] == \"admin\" THEN ALLOW END");
        var when = ast[0].WhenExpr;
        Assert.IsType<BinaryExpression>(when);
        var arrIdx = ((BinaryExpression)when).Left as ArrayIndexExpression;
        Assert.NotNull(arrIdx);
        Assert.IsType<PropertyExpression>(arrIdx.Array);
        Assert.IsType<LiteralExpression>(arrIdx.Index);
    }

    [Fact]
    public void PARSE_ERR_003_HeterogeneousArray()
    {
        // Parser should parse this fine; Semantic Analyzer will reject it later
        var ast = ParseCode("RULE r LANGUAGE 2 WHEN LENGTH([1, \"hello\"]) == 2 THEN ALLOW END");
        Assert.IsType<BinaryExpression>(ast[0].WhenExpr);
    }
}
