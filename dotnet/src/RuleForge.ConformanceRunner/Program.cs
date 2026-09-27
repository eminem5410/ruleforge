using System.Text.Json;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using RuleForge.Core.Evaluation;
using RuleForge.Core.Orchestration;

var rulePath = args[0];
var dataPath = args[1];

var schema = new Dictionary<string, Dictionary<string, string>> {
    { "customer", new() { {"age", "Integer"}, {"name", "String"}, {"active", "Boolean"}, {"email", "String"}, {"tags", "Array<String>"}, {"birth_date", "Date"}, {"registration_date", "Date"}, {"id", "Integer"}, {"risk_score", "Integer"}, {"status", "String"} } },
    { "invoice", new() { {"total", "Decimal"}, {"amount", "Decimal"}, {"status", "String"}, {"issue_date", "Date"}, {"due_date", "Date"} } },
    { "observation", new() { {"code", "String"}, {"value", "Decimal"}, {"unit", "String"} } }
};

var source = File.ReadAllText(rulePath);
var json = File.ReadAllText(dataPath);
var data = JsonDocument.Parse(json).RootElement;

try {
    var tokens = new Lexer(source).Tokenize();
    var ast = new Parser(tokens).Parse();

    var ctx = new Dictionary<string, object?>();
    if (data.TryGetProperty("context", out var ctxEl)) {
        ctx = DeserializeContext(ctxEl);
    }

    // V10: Use RuleEngine to support SET patches
    var engine = new RuleEngine(ast, schema, useCompiler: false);
    var pipelineResult = engine.Execute(ctx);
    var d = pipelineResult.Decisions[pipelineResult.Decisions.Count - 1];
    
    var actions = d.Actions.Select(a => new { action_type = a.ActionType, value = a.Value, payload = a.Payload }).ToList();
    Console.WriteLine(JsonSerializer.Serialize(new { code = (string?)null, matched = d.Matched, actions }));
} catch (Exception ex) when (ex is LexerException || ex is ParserException || ex is SemanticException || ex is EvaluatorException) {
    string? code = ex switch {
        LexerException le => le.Code,
        ParserException pe => pe.Code,
        SemanticException se => se.Code,
        EvaluatorException ee => ee.Code,
        _ => null
    };
    Console.WriteLine(JsonSerializer.Serialize(new { code, matched = false, actions = Array.Empty<object>() }));
}

Dictionary<string, object?> DeserializeContext(JsonElement el) {
    var dict = new Dictionary<string, object?>();
    foreach (var prop in el.EnumerateObject()) dict[prop.Name] = DeserializeValue(prop.Value);
    return dict;
}

object? DeserializeValue(JsonElement el) => el.ValueKind switch {
    JsonValueKind.String => el.GetString(),
    JsonValueKind.Number => el.TryGetDecimal(out var d) ? d : el.GetInt64(),
    JsonValueKind.True => true,
    JsonValueKind.False => false,
    JsonValueKind.Array => el.EnumerateArray().Select(DeserializeValue).ToList<object?>(),
    JsonValueKind.Object => DeserializeContext(el),
    _ => null
};
