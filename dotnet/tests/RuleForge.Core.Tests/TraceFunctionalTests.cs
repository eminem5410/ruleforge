using System;
using System.Collections.Generic;
using RuleForge.Core.Evaluation;
using RuleForge.Core.Lexing;
using RuleForge.Core.Orchestration;
using RuleForge.Core.Parsing;
using Xunit;

namespace RuleForge.Core.Tests;

public class TraceFunctionalTests
{
    private static readonly Dictionary<string, Dictionary<string, string>> Schema = new()
    {
        ["customer"] = new Dictionary<string, string>
        {
            ["age"] = "Integer",
            ["active"] = "Boolean",
            ["email"] = "String",
            ["tags"] = "Array<String>",
            ["birth_date"] = "Date",
            ["balance"] = "Decimal"
        }
    };

    private static TraceNode? GetTrace(string source, Dictionary<string, object?> context)
    {
        var tokens = new Lexer(source).Tokenize();
        var ast = new Parser(tokens).Parse();
        var engine = new RuleEngine(ast, Schema);
        var result = engine.Execute(context, trace: true);
        return result.Trace?[0].EvaluationTrace;
    }

    private static Dictionary<string, object?> Ctx(params (string, object?)[] props)
    {
        var customer = new Dictionary<string, object?>();
        foreach (var (k, v) in props) customer[k] = v;
        return new Dictionary<string, object?> { ["customer"] = customer };
    }

    [Fact]
    public void Test_001_Simple_Comparison()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END",
            Ctx(("age", 20)));

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal(">=", trace.Operator);
        Assert.Equal(true, trace.Value);
        Assert.Equal("Boolean", trace.Type);
        Assert.False(trace.ShortCircuited);

        var children = trace.Children;
        Assert.NotEmpty(children);
        Assert.Equal("PropertyExpression", children[0].NodeType);
        Assert.Equal(20, children[0].Value);
        Assert.Equal("Integer", children[0].Type);
        Assert.Equal("Literal", children[1].NodeType);
        Assert.Equal(18, children[1].Value);
        Assert.Equal("Integer", children[1].Type);
    }

    [Fact]
    public void Test_002_Logical_And_Both_Evaluated()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true THEN ALLOW END",
            Ctx(("age", 20), ("active", true)));

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal("AND", trace.Operator);
        Assert.Equal(true, trace.Value);
        Assert.False(trace.ShortCircuited);

        var children = trace.Children;
        Assert.NotEmpty(children);
        Assert.Equal("BinaryExpression", children[0].NodeType);
        Assert.Equal(">=", children[0].Operator);
        Assert.Equal("BinaryExpression", children[1].NodeType);
        Assert.Equal("==", children[1].Operator);
    }

    [Fact]
    public void Test_003_And_Short_Circuit_Phantom()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 1 WHEN customer.active == true AND customer.age >= 18 THEN ALLOW END",
            Ctx(("active", false), ("age", 20)));

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal("AND", trace.Operator);
        Assert.Equal(false, trace.Value);
        Assert.False(trace.ShortCircuited);

        var leftChild = trace.Children[0];
        Assert.Equal(false, leftChild.Value);

        var rightChild = trace.Children[1];
        Assert.True(rightChild.ShortCircuited);
        Assert.Null(rightChild.Value);
        Assert.Empty(rightChild.Children);
    }

    [Fact]
    public void Test_004_Null_Check()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALLOW END",
            Ctx());

        Assert.NotNull(trace);
        Assert.Equal("NullCheck", trace!.NodeType);
        Assert.Equal("IS NULL", trace.Operator);
        Assert.Equal(true, trace.Value);
        Assert.Equal("Boolean", trace.Type);

        Assert.Single(trace.Children);
        Assert.Equal("PropertyExpression", trace.Children[0].NodeType);
        Assert.Null(trace.Children[0].Value);
    }

    [Fact]
    public void Test_005_And_Short_Circuit_Avoids_Division_By_Zero()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 1 WHEN customer.active == true AND customer.age / 0 == 1 THEN ALLOW END",
            Ctx(("active", false), ("age", 20)));

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal("AND", trace.Operator);
        Assert.Equal(false, trace.Value);

        var phantom = trace.Children[1];
        Assert.True(phantom.ShortCircuited);
        Assert.Null(phantom.Value);
        Assert.Empty(phantom.Children);
    }

    [Fact]
    public void Test_006_Or_Short_Circuit_Phantom()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 1 WHEN customer.active == true OR customer.age / 0 == 1 THEN ALLOW END",
            Ctx(("active", true), ("age", 20)));

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal("OR", trace.Operator);
        Assert.Equal(true, trace.Value);

        Assert.True(trace.Children[1].ShortCircuited);
        Assert.Null(trace.Children[1].Value);
    }

    [Fact]
    public void Test_007_Filter_Trace()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 2 WHEN LENGTH(FILTER customer.tags WHERE it == \"vip\") == 1 THEN ALLOW END",
            Ctx(("tags", new List<object?> { "admin", "vip", "user" })));

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal("==", trace.Operator);

        var lengthNode = trace.Children[0];
        Assert.Equal("FunctionCall", lengthNode.NodeType);

        var filterNode = lengthNode.Children[0];
        Assert.Equal("FilterMap", filterNode.NodeType);
        Assert.Equal("FILTER", filterNode.Operator);
        Assert.NotNull(filterNode.Value);

        var filterChildren = filterNode.Children;
        Assert.NotEmpty(filterChildren);
        Assert.Equal("PropertyExpression", filterChildren[0].NodeType);
        Assert.Equal("BinaryExpression", filterChildren[1].NodeType);
        Assert.Equal("BinaryExpression", filterChildren[2].NodeType);
        Assert.Equal("BinaryExpression", filterChildren[3].NodeType);
    }

    [Fact]
    public void Test_008_Any_Short_Circuit()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE it == \"vip\" THEN ALLOW END",
            Ctx(("tags", new List<object?> { "admin", "vip", "user" })));

        Assert.NotNull(trace);
        Assert.Equal("AnyAll", trace!.NodeType);
        Assert.Equal("ANY", trace.Operator);
        Assert.Equal(true, trace.Value);

        var children = trace.Children;
        Assert.NotEmpty(children);
        Assert.Equal("PropertyExpression", children[0].NodeType);
        Assert.False(children[1].ShortCircuited);
        Assert.False(children[2].ShortCircuited);
        Assert.True(children[3].ShortCircuited);
        Assert.Null(children[3].Value);
    }

    [Fact]
    public void Test_009_Trace_False_No_EvaluationTrace()
    {
        var tokens = new Lexer(
            "RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END").Tokenize();
        var ast = new Parser(tokens).Parse();
        var engine = new RuleEngine(ast, Schema);
        var result = engine.Execute(Ctx(("age", 20)), trace: false);

        Assert.Null(result.Trace);
    }

    [Fact]
    public void Test_010_Trace_True_Has_EvaluationTrace()
    {
        var tokens = new Lexer(
            "RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END").Tokenize();
        var ast = new Parser(tokens).Parse();
        var engine = new RuleEngine(ast, Schema);
        var result = engine.Execute(Ctx(("age", 20)), trace: true);

        Assert.NotNull(result.Trace);
        Assert.Single(result.Trace!);

        var et = result.Trace![0].EvaluationTrace;
        Assert.NotNull(et);
        Assert.Equal("BinaryExpression", et!.NodeType);
        Assert.Equal(">=", et.Operator);
    }

    [Fact]
    public void Test_011_Error_Capture_At_Failing_Node()
    {
        var tokens = new Lexer(
            "RULE r LANGUAGE 1 WHEN customer.age / 0 > 1 THEN ALLOW END").Tokenize();
        var ast = new Parser(tokens).Parse();
        var context = Ctx(("age", 20));

        var evaluator = new Evaluator(context, deepTrace: true);

        var ex = Assert.Throws<EvaluatorException>(() => evaluator.EvaluateRule(ast[0]));
        Assert.Equal("RF4001", ex.Code);

        Assert.NotNull(evaluator.LastTrace);
        Assert.Equal("BinaryExpression", evaluator.LastTrace!.NodeType);
        Assert.Equal("RF4001", evaluator.LastTrace.ErrorCode);
        Assert.Null(evaluator.LastTrace.Value);
        Assert.NotNull(evaluator.LastTrace.ErrorMessage);
    }

    [Fact]
    public void Test_012_Map_Trace()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 2 WHEN LENGTH(MAP customer.tags USING it) == 3 THEN ALLOW END",
            Ctx(("tags", new List<object?> { "admin", "vip", "user" })));

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal("==", trace.Operator);
        Assert.Equal(true, trace.Value);

        var lengthNode = trace.Children[0];
        Assert.Equal("FunctionCall", lengthNode.NodeType);

        var mapNode = lengthNode.Children[0];
        Assert.Equal("FilterMap", mapNode.NodeType);
        Assert.Equal("MAP", mapNode.Operator);

        var mapChildren = mapNode.Children;
        Assert.NotEmpty(mapChildren);
        Assert.Equal("PropertyExpression", mapChildren[0].NodeType);
        Assert.Equal("Literal", mapChildren[1].NodeType);
        Assert.Equal("Literal", mapChildren[2].NodeType);
        Assert.Equal("Literal", mapChildren[3].NodeType);
    }

    [Fact]
    public void Test_013_All_Short_Circuit()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 2 WHEN ALL customer.tags WHERE it == \"admin\" THEN ALLOW END",
            Ctx(("tags", new List<object?> { "admin", "vip", "user" })));

        Assert.NotNull(trace);
        Assert.Equal("AnyAll", trace!.NodeType);
        Assert.Equal("ALL", trace.Operator);
        Assert.Equal(false, trace.Value);

        var children = trace.Children;
        Assert.NotEmpty(children);
        Assert.Equal("PropertyExpression", children[0].NodeType);
        Assert.False(children[0].ShortCircuited);
        Assert.False(children[1].ShortCircuited);
        Assert.False(children[2].ShortCircuited);
        Assert.True(children[3].ShortCircuited);
        Assert.Null(children[3].Value);
    }

    [Fact]
    public void Test_014_Array_Literal_Trace()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 2 WHEN LENGTH([1, 2, 3]) == 3 THEN ALLOW END",
            new Dictionary<string, object?>());

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal("==", trace.Operator);
        Assert.Equal(true, trace.Value);

        var lengthNode = trace.Children[0];
        Assert.Equal("FunctionCall", lengthNode.NodeType);

        var arrayNode = lengthNode.Children[0];
        Assert.Equal("ArrayLiteral", arrayNode.NodeType);

        var arrChildren = arrayNode.Children;
        Assert.NotEmpty(arrChildren);
        Assert.Equal("Literal", arrChildren[0].NodeType);
        Assert.Equal(1, arrChildren[0].Value);
        Assert.Equal("Literal", arrChildren[1].NodeType);
        Assert.Equal(2, arrChildren[1].Value);
        Assert.Equal("Literal", arrChildren[2].NodeType);
        Assert.Equal(3, arrChildren[2].Value);
    }

    [Fact]
    public void Test_015_Date_Comparison_Trace()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 1 WHEN customer.birth_date > DATE \"1990-01-01\" THEN ALLOW END",
            Ctx(("birth_date", new DateOnly(1995, 5, 20))));

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal(">", trace.Operator);
        Assert.Equal(true, trace.Value);
        Assert.Equal("Boolean", trace.Type);

        var leftChild = trace.Children[0];
        Assert.Equal("PropertyExpression", leftChild.NodeType);
        Assert.Equal("Date", leftChild.Type);
        Assert.Equal("1995-05-20", leftChild.Value);

        var rightChild = trace.Children[1];
        Assert.Equal("DateLiteral", rightChild.NodeType);
        Assert.Equal("Date", rightChild.Type);
    }

    [Fact]
    public void Test_016_Decimal_Comparison_Trace()
    {
        var trace = GetTrace(
            "RULE r LANGUAGE 1 WHEN customer.balance >= 100.50 THEN ALLOW END",
            Ctx(("balance", 150.75m)));

        Assert.NotNull(trace);
        Assert.Equal("BinaryExpression", trace!.NodeType);
        Assert.Equal(">=", trace.Operator);
        Assert.Equal(true, trace.Value);
        Assert.Equal("Boolean", trace.Type);

        var leftChild = trace.Children[0];
        Assert.Equal("PropertyExpression", leftChild.NodeType);
        Assert.Equal("Decimal", leftChild.Type);

        var rightChild = trace.Children[1];
        Assert.Equal("Literal", rightChild.NodeType);
        Assert.Equal("Decimal", rightChild.Type);
    }

    [Fact]
    public void TraceFalse_DoesNotProduceEvaluationTrace()
    {
        var schema = new Dictionary<string, Dictionary<string, string>>
        {
            ["customer"] = new Dictionary<string, string>
            {
                ["age"] = "Integer"
            }
        };

        var tokens = new Lexer(
            "RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END"
        ).Tokenize();

        var ast = new Parser(tokens).Parse();
        var engine = new RuleEngine(ast, schema);

        var context = new Dictionary<string, object?>
        {
            ["customer"] = new Dictionary<string, object?>
            {
                ["age"] = 20
            }
        };

        var result = engine.Execute(context, trace: false);

        Assert.NotEmpty(result.Decisions);
        Assert.Null(result.Trace);
    }

}