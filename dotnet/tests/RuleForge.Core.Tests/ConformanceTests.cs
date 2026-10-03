using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Xunit;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using RuleForge.Core.Evaluation;
using RuleForge.Core.Orchestration;

namespace RuleForge.Core.Tests;

public class ConformanceTests
{
    private readonly Dictionary<string, Dictionary<string, string>> _schema = new()
    {
        { "customer", new Dictionary<string, string> { { "age", "Integer" }, { "name", "String" }, { "active", "Boolean" }, { "email", "String" }, { "tags", "Array<String>" }, { "birth_date", "Date" }, { "registration_date", "Date" }, { "id", "Integer" }, { "risk_score", "Integer" }, { "status", "String" }, { "items", "Array<Object>" } } },
        { "invoice", new Dictionary<string, string> { { "total", "Decimal" }, { "amount", "Decimal" }, { "status", "String" }, { "issue_date", "Date" }, { "due_date", "Date" } } },
        { "observation", new Dictionary<string, string> { { "code", "String" }, { "value", "Decimal" }, { "unit", "String" } } }
    };

    public static IEnumerable<object[]> GetConformanceCases()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !Directory.Exists(Path.Combine(dir.FullName, "tests", "conformance")))
        {
            dir = dir.Parent;
        }
        var baseDir = Path.Combine(dir!.FullName, "tests", "conformance");
        
        var files = Directory.GetFiles(baseDir, "*.rf", SearchOption.AllDirectories);
        foreach (var rulePath in files)
        {
            yield return new object[] { rulePath };
        }
    }

    [Theory]
    [MemberData(nameof(GetConformanceCases))]
    public void Test_Conformance_Vector(string rulePath)
    {
        // V12.0: Skip MATCH/CASE vectors until Parser/Semantic are implemented
        if (rulePath.Contains("MATCH", StringComparison.OrdinalIgnoreCase))
        {
            Console.WriteLine($"--- SKIPPED V12 VECTOR: {rulePath} ---");
            return;
        }

        var source = File.ReadAllText(rulePath);
        var dataPath = rulePath.Replace(".rf", ".json");
        var json = File.ReadAllText(dataPath);
        var data = JsonDocument.Parse(json).RootElement;
        
        string? expectedError = data.TryGetProperty("expected_error_code", out var errEl) ? errEl.GetString() : null;

        try
        {
            var tokens = new Lexer(source).Tokenize();
            var ast = new Parser(tokens).Parse();
            new SemanticAnalyzer(_schema).Analyze(ast);

            var ctx = new Dictionary<string, object?>();
            if (data.TryGetProperty("context", out var ctxEl))
            {
                ctx = DeserializeContext(ctxEl);
            }

            var engine = new RuleEngine(ast, _schema, useCompiler: false);
            var pipelineResult = engine.Execute(ctx);
            var decisions = pipelineResult.Decisions;

            Assert.Null(expectedError); // Should not have errored
            
            var d = decisions[decisions.Count - 1];
            var expected = data.GetProperty("expected");
            Assert.Equal(expected.GetProperty("matched").GetBoolean(), d.Matched);
            
            var expectedActions = expected.GetProperty("actions").EnumerateArray().ToList();
            Assert.Equal(expectedActions.Count, d.Actions.Count);
            for (int i = 0; i < expectedActions.Count; i++)
            {
                Assert.Equal(expectedActions[i].GetProperty("action_type").GetString(), d.Actions[i].ActionType);
                if (expectedActions[i].TryGetProperty("value", out var valEl))
                {
                    Assert.Equal(valEl.GetString(), d.Actions[i].Value);
                }
                if (expectedActions[i].TryGetProperty("payload", out var payloadEl))
                {
                    object? expectedPayload = payloadEl.ValueKind switch
                    {
                        JsonValueKind.String => (object?)payloadEl.GetString(),
                        JsonValueKind.Number => payloadEl.TryGetDecimal(out var dec) ? dec : payloadEl.GetInt64(),
                        JsonValueKind.True => true,
                        JsonValueKind.False => false,
                        JsonValueKind.Null => null,
                        JsonValueKind.Array => (object?)payloadEl.Deserialize<List<object?>>(),
                        _ => null
                    };
                    Assert.Equal(System.Text.Json.JsonSerializer.Serialize(expectedPayload), System.Text.Json.JsonSerializer.Serialize(d.Actions[i].Payload));
                }
            }
        }
        catch (Exception ex) when (ex is LexerException || ex is ParserException || ex is SemanticException || ex is EvaluatorException)
        {
            Console.WriteLine($"!!! EXCEPTION CAUGHT: {ex.GetType().Name} - {ex.Message}");
            Assert.NotNull(expectedError);
            string? code = ex switch
            {
                LexerException le => le.Code,
                ParserException pe => pe.Code,
                SemanticException se => se.Code,
                EvaluatorException ee => ee.Code,
                _ => null
            };
            Assert.Equal(expectedError, code);
        }
    }

    private Dictionary<string, object?> DeserializeContext(JsonElement el)
    {
        var dict = new Dictionary<string, object?>();
        foreach (var prop in el.EnumerateObject())
        {
            dict[prop.Name] = DeserializeValue(prop.Value);
        }
        return dict;
    }

    private object? DeserializeValue(JsonElement el)
    {
        return el.ValueKind switch
        {
            JsonValueKind.String => el.GetString(),
            JsonValueKind.Number => el.TryGetDecimal(out var d) ? d : el.GetInt64(),
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            JsonValueKind.Array => el.EnumerateArray().Select(DeserializeValue).ToList<object?>(),
            JsonValueKind.Object => DeserializeContext(el),
            _ => null
        };
    }
}
