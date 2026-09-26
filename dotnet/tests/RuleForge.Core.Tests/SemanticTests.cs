using Xunit;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using System.Collections.Generic;

namespace RuleForge.Core.Tests;

public class SemanticTests
{
    private readonly Dictionary<string, Dictionary<string, string>> _schema = new()
    {
        { "customer", new Dictionary<string, string> { { "age", "Integer" }, { "name", "String" }, { "active", "Boolean" }, { "tags", "Array<String>" } } }
    };

    private void AnalyzeCode(string source)
    {
        var tokens = new Lexer(source).Tokenize();
        var ast = new Parser(tokens).Parse();
        new SemanticAnalyzer(_schema).Analyze(ast);
    }

    [Fact]
    public void SEM_Valid_Rule()
    {
        var ex = Record.Exception(() => AnalyzeCode("RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END"));
        Assert.Null(ex);
    }

    [Fact]
    public void SEM_ERR_001_TypeMismatch()
    {
        var ex = Assert.Throws<SemanticException>(() => AnalyzeCode("RULE r LANGUAGE 1 WHEN customer.age > \"18\" THEN ALLOW END"));
        Assert.Equal("RF3001", ex.Code);
        Assert.Contains("requires numeric/date", ex.Message);
    }

    [Fact]
    public void SEM_ERR_002_UnknownProperty()
    {
        var ex = Assert.Throws<SemanticException>(() => AnalyzeCode("RULE r LANGUAGE 1 WHEN customer.salary > 100 THEN ALLOW END"));
        Assert.Equal("RF3002", ex.Code);
        Assert.Contains("Property 'salary' not found", ex.Message);
    }

    [Fact]
    public void SEM_ERR_003_MultipleTerminals()
    {
        var ex = Assert.Throws<SemanticException>(() => AnalyzeCode("RULE r LANGUAGE 1 WHEN true THEN ALLOW DENY \"No\" END"));
        Assert.Equal("RF3002", ex.Code);
        Assert.Contains("ONE terminal decision", ex.Message);
    }

    [Fact]
    public void SEM_ERR_004_WhenNotBoolean()
    {
        var ex = Assert.Throws<SemanticException>(() => AnalyzeCode("RULE r LANGUAGE 1 WHEN customer.age + 10 THEN ALLOW END"));
        Assert.Equal("RF3002", ex.Code);
        Assert.Contains("WHEN condition must evaluate to Boolean", ex.Message);
    }

    // --- V7 Array Tests ---

    [Fact]
    public void SEM_007_ArrayLiteralAndLength()
    {
        var ex = Record.Exception(() => AnalyzeCode("RULE r LANGUAGE 2 WHEN LENGTH([1, 2, 3]) == 3 THEN ALLOW END"));
        Assert.Null(ex);
    }

    [Fact]
    public void SEM_008_ArrayLiteralAndContains()
    {
        var ex = Record.Exception(() => AnalyzeCode("RULE r LANGUAGE 2 WHEN CONTAINS([1, 2, 3], 2) THEN ALLOW END"));
        Assert.Null(ex);
    }

    [Fact]
    public void SEM_009_ArrayIndexing()
    {
        var ex = Record.Exception(() => AnalyzeCode("RULE r LANGUAGE 2 WHEN customer.tags[0] == \"admin\" THEN ALLOW END"));
        Assert.Null(ex);
    }

    [Fact]
    public void SEM_ERR_003_HeterogeneousArray()
    {
        var ex = Assert.Throws<SemanticException>(() => AnalyzeCode("RULE r LANGUAGE 2 WHEN LENGTH([1, \"hello\"]) == 2 THEN ALLOW END"));
        Assert.Equal("RF3003", ex.Code);
        Assert.Contains("Heterogeneous array literal", ex.Message);
    }
}
