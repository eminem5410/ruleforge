using System.Collections.Generic;
using System.Linq;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using Xunit;

namespace RuleForge.Core.Tests;

public class SecurityTests
{
    private static void AnalyzeWith(string source, Dictionary<string, Dictionary<string, string>>? schema = null)
    {
        var tokens = new Lexer(source).Tokenize();
        var ast = new Parser(tokens).Parse();
        new SemanticAnalyzer(schema ?? new Dictionary<string, Dictionary<string, string>>()).Analyze(ast);
    }

    [Fact]
    public void T_RF5001_DepthExceeded()
    {
        var expr = string.Join(" OR ", Enumerable.Repeat("1 == 1", 52));
        var ex = Assert.Throws<SemanticException>(() =>
            AnalyzeWith($"RULE r LANGUAGE 1 WHEN {expr} THEN ALLOW END"));
        Assert.Equal("RF5001", ex.Code);
    }

    [Fact]
    public void T_RF5002_NodeCountExceeded()
    {
        var elements = string.Join(", ", Enumerable.Range(1, 502));
        var ex = Assert.Throws<SemanticException>(() =>
            AnalyzeWith($"RULE r LANGUAGE 2 WHEN LENGTH([{elements}]) == 502 THEN ALLOW END"));
        Assert.Equal("RF5002", ex.Code);
    }

    [Theory]
    [InlineData("ANY", "WHERE", false)]
    [InlineData("ALL", "WHERE", false)]
    [InlineData("FILTER", "WHERE", true)]
    [InlineData("MAP", "USING", true)]
    public void T_RF5001_ArrayOpDepth(string op, string keyword, bool wrapper)
    {
        var needed = wrapper ? 47 : 49;
        var inner = "1 == 1";
        for (int i = 0; i < needed; i++)
            inner = $"({inner} AND 1 == 1)";
        var schema = new Dictionary<string, Dictionary<string, string>>
        {
            ["customer"] = new() { ["tags"] = "Array<String>" }
        };
        string code = wrapper
            ? $"RULE r LANGUAGE 2 WHEN LENGTH({op} customer.tags {keyword} {inner}) == 0 THEN ALLOW END"
            : $"RULE r LANGUAGE 2 WHEN {op} customer.tags {keyword} {inner} THEN ALLOW END";
        var ex = Assert.Throws<SemanticException>(() => AnalyzeWith(code, schema));
        Assert.Equal("RF5001", ex.Code);
    }

    [Theory]
    [InlineData("ANY", "WHERE", false)]
    [InlineData("ALL", "WHERE", false)]
    [InlineData("FILTER", "WHERE", true)]
    [InlineData("MAP", "USING", true)]
    public void T_RF5002_ArrayOpNodeCount(string op, string keyword, bool wrapper)
    {
        var elements = string.Join(", ", Enumerable.Range(1, 502));
        string code = wrapper
            ? $"RULE r LANGUAGE 2 WHEN LENGTH({op} [{elements}] {keyword} it) == 502 THEN ALLOW END"
            : $"RULE r LANGUAGE 2 WHEN {op} [{elements}] {keyword} it THEN ALLOW END";
        var ex = Assert.Throws<SemanticException>(() => AnalyzeWith(code));
        Assert.Equal("RF5002", ex.Code);
    }

    [Fact]
    public void T_RF5001_NullCheckDepth()
    {
        var inner = "customer.age";
        for (int i = 0; i < 50; i++)
            inner = $"({inner} + 1)";
        var schema = new Dictionary<string, Dictionary<string, string>>
        {
            ["customer"] = new() { ["age"] = "Integer" }
        };
        var ex = Assert.Throws<SemanticException>(() =>
            AnalyzeWith($"RULE r LANGUAGE 1 WHEN {inner} IS NULL THEN ALLOW END", schema));
        Assert.Equal("RF5001", ex.Code);
    }
}
