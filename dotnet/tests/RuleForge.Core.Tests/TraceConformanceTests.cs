using System;
using System.Collections.Generic;
using System.Linq;
using RuleForge.Core.Evaluation;
using RuleForge.Core.Lexing;
using RuleForge.Core.Orchestration;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using Xunit;

namespace RuleForge.Core.Tests;

public class TraceConformanceTests
{
    private static readonly Dictionary<string, Dictionary<string, string>> Schema = new()
    {
        ["customer"] = new Dictionary<string, string>
        {
            ["age"] = "Integer", ["active"] = "Boolean", ["email"] = "String",
            ["tags"] = "Array<String>", ["birth_date"] = "Date", ["balance"] = "Decimal"
        }
    };

    private static TraceNode? GetTrace(string src, Dictionary<string, object?> ctx)
    {
        var tokens = new Lexer(src).Tokenize();
        var ast = new Parser(tokens).Parse();
        var engine = new RuleEngine(ast, Schema);
        return engine.Execute(ctx, trace: true).Trace?[0].EvaluationTrace;
    }

    private static TraceNode? GetErrorTrace(string src, Dictionary<string, object?> ctx)
    {
        var tokens = new Lexer(src).Tokenize();
        var ast = new Parser(tokens).Parse();
        new SemanticAnalyzer(Schema).Analyze(ast);
        var ev = new Evaluator(ctx, deepTrace: true);
        try { ev.EvaluateRule(ast[0]); } catch { }
        return ev.LastTrace;
    }

    private static void CheckNode(TraceNode? t, string? nt = null, string? op = null,
        object? val = null, string? type = null, bool? sc = null, int? cc = null, string? ec = null)
    {
        Assert.NotNull(t);
        if (nt != null) Assert.Equal(nt, t!.NodeType);
        if (op != null) Assert.Equal(op, t.Operator);
        if (type != null) Assert.Equal(type, t.Type);
        if (sc.HasValue) Assert.Equal(sc.Value, t.ShortCircuited);
        if (cc.HasValue) Assert.True(t.Children.Count == cc.Value, $"Children: {t.Children.Count}");
        if (val != null) Assert.Equal(val, t.Value);
        if (ec != null) Assert.Equal(ec, t.ErrorCode);
    }

    private static Dictionary<string, object?> Ctx(params (string, object?)[] props)
    {
        var customer = new Dictionary<string, object?>();
        foreach (var (k, v) in props) customer[k] = v;
        return new Dictionary<string, object?> { ["customer"] = customer };
    }

    [Fact] public void T001_Comparison()
    {
        var t = GetTrace("RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END",
            Ctx(("age", 20)));
        CheckNode(t, "BinaryExpression", ">=", true, "Boolean", false, 2);
        CheckNode(t!.Children[0], "PropertyExpression", val: 20, type: "Integer");
        CheckNode(t.Children[1], "Literal", val: 18, type: "Integer");
    }

    [Fact] public void T002_AndNormal()
    {
        var t = GetTrace("RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true THEN ALLOW END",
            Ctx(("age", 20), ("active", true)));
        CheckNode(t, "BinaryExpression", "AND", true, null, false, 2);
        CheckNode(t!.Children[0], "BinaryExpression", ">=");
        CheckNode(t.Children[1], "BinaryExpression", "==");
    }

    [Fact] public void T003_AndShortCircuit()
    {
        var t = GetTrace("RULE r LANGUAGE 1 WHEN customer.active == true AND customer.age >= 18 THEN ALLOW END",
            Ctx(("active", false), ("age", 20)));
        CheckNode(t, "BinaryExpression", "AND", false, null, false, 2);
        CheckNode(t!.Children[0], "BinaryExpression", val: false);
        CheckNode(t.Children[1], "BinaryExpression", sc: true);
        Assert.Null(t.Children[1].Value);
    }

    [Fact] public void T004_OrShortCircuit()
    {
        var t = GetTrace("RULE r LANGUAGE 1 WHEN customer.active == true OR customer.age >= 18 THEN ALLOW END",
            Ctx(("active", true), ("age", 20)));
        CheckNode(t, "BinaryExpression", "OR", true, null, false, 2);
        CheckNode(t!.Children[0], "BinaryExpression", val: true);
        CheckNode(t.Children[1], "BinaryExpression", sc: true);
    }

    [Fact] public void T005_NullCheck()
    {
        var t = GetTrace("RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALLOW END",
            Ctx());
        CheckNode(t, "NullCheck", "IS NULL", true, "Boolean", null, 1);
        CheckNode(t!.Children[0], "PropertyExpression");
        Assert.Null(t.Children[0].Value);
    }

    [Fact] public void T006_Filter()
    {
        var t = GetTrace("RULE r LANGUAGE 2 WHEN LENGTH(FILTER customer.tags WHERE it == \"vip\") == 1 THEN ALLOW END",
            Ctx(("tags", new List<object?> { "admin", "vip", "user" })));
        CheckNode(t, "BinaryExpression", "==", true, null, null, 2);
        CheckNode(t!.Children[0], "FunctionCall", cc: 1);
        CheckNode(t.Children[0].Children[0], "FilterMap", op: "FILTER", cc: 4);
    }

    [Fact] public void T007_Map()
    {
        var t = GetTrace("RULE r LANGUAGE 2 WHEN LENGTH(MAP customer.tags USING it) == 3 THEN ALLOW END",
            Ctx(("tags", new List<object?> { "admin", "vip", "user" })));
        CheckNode(t, "BinaryExpression", "==", true, null, null, 2);
        CheckNode(t!.Children[0], "FunctionCall", cc: 1);
        CheckNode(t.Children[0].Children[0], "FilterMap", op: "MAP", cc: 4);
    }

    [Fact] public void T008_Any()
    {
        var t = GetTrace("RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE it == \"vip\" THEN ALLOW END",
            Ctx(("tags", new List<object?> { "admin", "vip", "user" })));
        CheckNode(t, "AnyAll", "ANY", true, null, null, 4);
        Assert.False(t!.Children[1].ShortCircuited);
        Assert.False(t.Children[2].ShortCircuited);
        Assert.True(t.Children[3].ShortCircuited);
        Assert.Null(t.Children[3].Value);
    }

    [Fact] public void T009_All()
    {
        var t = GetTrace("RULE r LANGUAGE 2 WHEN ALL customer.tags WHERE it == \"admin\" THEN ALLOW END",
            Ctx(("tags", new List<object?> { "admin", "vip", "user" })));
        CheckNode(t, "AnyAll", "ALL", false, null, null, 4);
        Assert.False(t!.Children[1].ShortCircuited);
        Assert.False(t.Children[2].ShortCircuited);
        Assert.True(t.Children[3].ShortCircuited);
        Assert.Null(t.Children[3].Value);
    }

    [Fact] public void T010_ArrayLiteral()
    {
        var t = GetTrace("RULE r LANGUAGE 2 WHEN LENGTH([1, 2, 3]) == 3 THEN ALLOW END",
            new Dictionary<string, object?>());
        CheckNode(t, "BinaryExpression", "==", true, null, null, 2);
        CheckNode(t!.Children[0], "FunctionCall", cc: 1);
        CheckNode(t.Children[0].Children[0], "ArrayLiteral", cc: 3);
    }

    [Fact] public void T011_ArrayIndex()
    {
        var t = GetTrace("RULE r LANGUAGE 2 WHEN customer.tags[0] == \"admin\" THEN ALLOW END",
            Ctx(("tags", new List<object?> { "admin", "vip", "user" })));
        CheckNode(t, "BinaryExpression", "==", true, null, null, 2);
        CheckNode(t!.Children[0], "ArrayIndex");
        CheckNode(t.Children[1], "Literal");
    }

    [Fact] public void T012_Date()
    {
        var t = GetTrace("RULE r LANGUAGE 1 WHEN customer.birth_date > DATE \"1990-01-01\" THEN ALLOW END",
            Ctx(("birth_date", new DateOnly(1995, 5, 20))));
        CheckNode(t, "BinaryExpression", ">", true, "Boolean", null, 2);
        CheckNode(t!.Children[0], "PropertyExpression", type: "Date");
        Assert.Equal("1995-05-20", t.Children[0].Value);
        CheckNode(t.Children[1], "DateLiteral", type: "Date");
    }

    [Fact] public void T013_Decimal()
    {
        var t = GetTrace("RULE r LANGUAGE 1 WHEN customer.balance >= 100.50 THEN ALLOW END",
            Ctx(("balance", 150.75m)));
        CheckNode(t, "BinaryExpression", ">=", true, "Boolean", null, 2);
        CheckNode(t!.Children[0], "PropertyExpression", val: "150.75", type: "Decimal");
        CheckNode(t.Children[1], "Literal", val: "100.50", type: "Decimal");
    }

    [Fact] public void T014_Error()
    {
        var t = GetErrorTrace("RULE r LANGUAGE 1 WHEN customer.age / 0 > 1 THEN ALLOW END",
            Ctx(("age", 20)));
        CheckNode(t, "BinaryExpression", op: "/", ec: "RF4001");
        Assert.Null(t!.Value);
    }

    [Fact] public void T015_Nested()
    {
        var t = GetTrace("RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true OR customer.email IS NULL THEN ALLOW END",
            Ctx(("age", 20), ("active", false), ("email", "test@test.com")));
        CheckNode(t, "BinaryExpression", "OR", false, null, false, 2);
        CheckNode(t!.Children[0], "BinaryExpression", "AND", val: false);
        CheckNode(t.Children[1], "NullCheck", "IS NULL", val: false);
    }

    [Fact] public void T016_DecimalPrecision()
    {
        var t = GetTrace("RULE r LANGUAGE 1 WHEN customer.balance >= 1.234567890123456789 THEN ALLOW END",
            Ctx(("balance", 1.234567890123456789m)));
        CheckNode(t, "BinaryExpression", ">=", true, "Boolean", null, 2);
        CheckNode(t!.Children[0], "PropertyExpression", val: "1.234567890123456789", type: "Decimal");
        CheckNode(t.Children[1], "Literal", val: "1.234567890123456789", type: "Decimal");
    }
}
