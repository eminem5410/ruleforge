using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace RuleForge.Api.Contracts;

public class EvaluateRequest
{
    [JsonPropertyName("source")]
    public string Source { get; set; } = string.Empty;
    
    [JsonPropertyName("context_schema")]
    public Dictionary<string, Dictionary<string, string>> ContextSchema { get; set; } = new();
    
    [JsonPropertyName("context")]
    public Dictionary<string, object?> Context { get; set; } = new();
}

public class EvaluateResponse
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = "ok";
    
    [JsonPropertyName("decisions")]
    public List<DecisionDto> Decisions { get; set; } = new();
}

public class DecisionDto
{
    [JsonPropertyName("rule_id")]
    public string RuleId { get; set; } = string.Empty;
    
    [JsonPropertyName("matched")]
    public bool Matched { get; set; }
    
    [JsonPropertyName("actions")]
    public List<ActionDto> Actions { get; set; } = new();
}

public class ActionDto
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = string.Empty;
    
    [JsonPropertyName("value")]
    public string? Value { get; set; }
}

public class ErrorResponse
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = "error";
    
    [JsonPropertyName("error_code")]
    public string ErrorCode { get; set; } = string.Empty;
}
