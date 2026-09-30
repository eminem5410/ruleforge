using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace RuleForge.Core.Evaluation;

/// <summary>
/// V11.2 Deep AST Trace node. Canonical structure shared across
/// Python and C# implementations. The trace is observability of
/// the semantics, not a second implementation of the semantics.
/// </summary>
public class TraceNode
{
    public string NodeType { get; set; } = "";

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Operator { get; set; }

    public object? Value { get; set; }

    public string Type { get; set; } = "";

    public List<TraceNode> Children { get; set; } = new();

    public bool ShortCircuited { get; set; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ErrorCode { get; set; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ErrorMessage { get; set; }
}
