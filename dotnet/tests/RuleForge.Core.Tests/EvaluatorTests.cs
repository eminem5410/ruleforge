using Xunit;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using RuleForge.Core.Evaluation;
using System.Collections.Generic;

namespace RuleForge.Core.Tests;

public class EvaluatorTests
{
    private readonly Dictionary<string, Dictionary<string, string>> _schema = new()
    {
        { "customer", new Dictionary<string, string> { { "age", "Integer" }, { "name", "String" }, { "active", "Boolean" }, { "email", "String" } } },
        { "invoice", new Dictionary<string, string> { { "total", "Decimal" } } }
    };

    private List<Decision> EvalCode(string source, Dictionary<string, object?> context)
    {
        var tokens = new Lexer(source).Tokenize();
        var ast = new Parser(tokens).Parse();
        new SemanticAnalyzer(_schema).Analyze(ast);
        return new Evaluator(context).EvaluateRules(ast);
    }

    [Fact]
    public void EVAL_001_BasicMatch()
    {
        var ctx = new Dictionary<string, object?> { { "customer", new Dictionary<string, object?> { { "age", 21 } } } };
        var decisions = EvalCode("RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END", ctx);
        Assert.True(decisions[0].Matched);
        Assert.Equal("ALLOW", decisions[0].Actions[0].ActionType);
    }

    [Fact]
    public void EVAL_002_ShortCircuitAnd()
    {
        var ctx = new Dictionary<string, object?> { { "customer", new Dictionary<string, object?> { { "active", false } } } };
        var decisions = EvalCode("RULE r LANGUAGE 1 WHEN customer.active == true AND 1/0 == 1 THEN ALLOW END", ctx);
        Assert.False(decisions[0].Matched); // Does not throw DivByZero
    }

    [Fact]
    public void EVAL_003_DecimalPrecision()
    {
        var ctx = new Dictionary<string, object?> { { "invoice", new Dictionary<string, object?> { { "total", 0.1m } } } };
        var decisions = EvalCode("RULE r LANGUAGE 1 WHEN invoice.total + 0.2 == 0.3 THEN ALLOW END", ctx);
        Assert.True(decisions[0].Matched);
    }

    [Fact]
    public void EVAL_ERR_001_DivisionByZero()
    {
        var ctx = new Dictionary<string, object?> { { "invoice", new Dictionary<string, object?> { { "total", 100.0m } } } };
        var ex = Assert.Throws<EvaluatorException>(() => EvalCode("RULE r LANGUAGE 1 WHEN invoice.total / 0 > 10 THEN ALLOW END", ctx));
        Assert.Equal("RF4001", ex.Code);
    }

    [Fact]
    public void EVAL_ERR_002_NullArithmetic()
    {
        var ctx = new Dictionary<string, object?> { { "customer", new Dictionary<string, object?>() } };
        var ex = Assert.Throws<EvaluatorException>(() => EvalCode("RULE r LANGUAGE 1 WHEN customer.age + 10 == 30 THEN ALLOW END", ctx));
        Assert.Equal("RF4002", ex.Code);
    }
}
