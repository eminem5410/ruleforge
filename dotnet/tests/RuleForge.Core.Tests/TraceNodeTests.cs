using System.Collections.Generic;
using System.Text.Json;
using RuleForge.Core.Evaluation;
using RuleForge.Core.Orchestration;
using Xunit;

namespace RuleForge.Core.Tests;

public class TraceNodeTests
{
    // === Serialization Tests ===

    [Fact]
    public void Test_Normal_Node_Omits_Null_Optional_Fields()
    {
        var node = new TraceNode
        {
            NodeType = "Literal",
            Value = 18,
            Type = "Integer",
            Children = new List<TraceNode>(),
            ShortCircuited = false
        };

        var json = JsonSerializer.Serialize(node);
        var doc = JsonDocument.Parse(json);

        // Obligatory fields present
        Assert.True(doc.RootElement.TryGetProperty("NodeType", out _));
        Assert.True(doc.RootElement.TryGetProperty("Value", out _));
        Assert.True(doc.RootElement.TryGetProperty("Type", out _));
        Assert.True(doc.RootElement.TryGetProperty("Children", out _));
        Assert.True(doc.RootElement.TryGetProperty("ShortCircuited", out _));

        // Optional fields omitted when null
        Assert.False(doc.RootElement.TryGetProperty("Operator", out _));
        Assert.False(doc.RootElement.TryGetProperty("ErrorCode", out _));
        Assert.False(doc.RootElement.TryGetProperty("ErrorMessage", out _));
    }

    [Fact]
    public void Test_Node_With_Operator_Includes_It()
    {
        var node = new TraceNode
        {
            NodeType = "BinaryExpression",
            Operator = "AND",
            Value = true,
            Type = "Boolean",
            Children = new List<TraceNode>(),
            ShortCircuited = false
        };

        var json = JsonSerializer.Serialize(node);
        var doc = JsonDocument.Parse(json);

        Assert.True(doc.RootElement.TryGetProperty("Operator", out var op));
        Assert.Equal("AND", op.GetString());
    }

    [Fact]
    public void Test_Error_Node_Includes_Error_Fields()
    {
        var node = new TraceNode
        {
            NodeType = "BinaryExpression",
            Operator = "/",
            Value = null,
            Type = "Null",
            Children = new List<TraceNode>(),
            ShortCircuited = false,
            ErrorCode = "RF4001",
            ErrorMessage = "Division by zero"
        };

        var json = JsonSerializer.Serialize(node);
        var doc = JsonDocument.Parse(json);

        Assert.True(doc.RootElement.TryGetProperty("ErrorCode", out var code));
        Assert.Equal("RF4001", code.GetString());

        Assert.True(doc.RootElement.TryGetProperty("ErrorMessage", out var msg));
        Assert.Equal("Division by zero", msg.GetString());

        // Value present as null (obligatory field, not omitted)
        Assert.True(doc.RootElement.TryGetProperty("Value", out var val));
        Assert.Equal(JsonValueKind.Null, val.ValueKind);
    }

    [Fact]
    public void Test_Phantom_Node_Structure()
    {
        var node = new TraceNode
        {
            NodeType = "BinaryExpression",
            Value = null,
            Type = "Null",
            Children = new List<TraceNode>(),
            ShortCircuited = true
        };

        var json = JsonSerializer.Serialize(node);
        var doc = JsonDocument.Parse(json);

        Assert.True(doc.RootElement.TryGetProperty("ShortCircuited", out var sc));
        Assert.True(sc.GetBoolean());

        Assert.True(doc.RootElement.TryGetProperty("Value", out var val));
        Assert.Equal(JsonValueKind.Null, val.ValueKind);

        Assert.True(doc.RootElement.TryGetProperty("Children", out var children));
        Assert.Equal(0, children.GetArrayLength());

        // Operator omitted (null)
        Assert.False(doc.RootElement.TryGetProperty("Operator", out _));
    }

    [Fact]
    public void Test_Nested_Children_Serialize_Correctly()
    {
        var parent = new TraceNode
        {
            NodeType = "BinaryExpression",
            Operator = "AND",
            Value = false,
            Type = "Boolean",
            Children = new List<TraceNode>
            {
                new TraceNode
                {
                    NodeType = "BinaryExpression",
                    Operator = "==",
                    Value = false,
                    Type = "Boolean",
                    Children = new List<TraceNode>(),
                    ShortCircuited = false
                },
                new TraceNode
                {
                    NodeType = "BinaryExpression",
                    Value = null,
                    Type = "Null",
                    Children = new List<TraceNode>(),
                    ShortCircuited = true
                }
            },
            ShortCircuited = false
        };

        var json = JsonSerializer.Serialize(parent);
        var doc = JsonDocument.Parse(json);

        Assert.True(doc.RootElement.TryGetProperty("Children", out var children));
        Assert.Equal(2, children.GetArrayLength());

        // First child: evaluated, has Operator
        Assert.True(children[0].TryGetProperty("Operator", out _));
        Assert.True(children[0].TryGetProperty("ShortCircuited", out var sc1));
        Assert.False(sc1.GetBoolean());

        // Second child: phantom, no Operator, ShortCircuited=true
        Assert.False(children[1].TryGetProperty("Operator", out _));
        Assert.True(children[1].TryGetProperty("ShortCircuited", out var sc2));
        Assert.True(sc2.GetBoolean());
    }

    // === RuleTraceEntry Structure Tests ===

    [Fact]
    public void Test_RuleTraceEntry_Has_EvaluationTrace()
    {
        var entry = new RuleTraceEntry
        {
            RuleName = "test_rule",
            RuleIndex = 0,
            Matched = false,
            AppliedPatches = new List<string>(),
            Actions = new List<string> { "ALLOW" },
            EvaluationTrace = new TraceNode
            {
                NodeType = "BinaryExpression",
                Value = false,
                Type = "Boolean",
                Children = new List<TraceNode>(),
                ShortCircuited = false
            }
        };

        Assert.NotNull(entry.EvaluationTrace);
        Assert.Equal("BinaryExpression", entry.EvaluationTrace.NodeType);
        Assert.Equal("Boolean", entry.EvaluationTrace.Type);
    }

    [Fact]
    public void Test_RuleTraceEntry_EvaluationTrace_Defaults_Null()
    {
        var entry = new RuleTraceEntry
        {
            RuleName = "test_rule",
            RuleIndex = 0,
            Matched = true,
            AppliedPatches = new List<string>(),
            Actions = new List<string> { "ALLOW" }
        };

        Assert.Null(entry.EvaluationTrace);
    }
}
