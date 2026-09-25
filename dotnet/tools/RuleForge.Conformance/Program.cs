using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using RuleForge.Core.Evaluation;

namespace RuleForge.Conformance;

public class Program
{
    public static int Main(string[] args)
    {
        string baseDir = Path.Combine(Directory.GetCurrentDirectory(), "conformance");
        if (!Directory.Exists(baseDir)) {
            baseDir = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "conformance"));
        }

        string manifestPath = Path.Combine(baseDir, "manifest.json");
        if (!File.Exists(manifestPath))
        {
            Console.WriteLine($"manifest.json not found at {manifestPath}!");
            return 1;
        }

        var manifest = JsonNode.Parse(File.ReadAllText(manifestPath))!;
        var vectors = manifest["vectors"]!.AsArray();
        
        Console.WriteLine("RuleForge .NET Conformance Runner");
        Console.WriteLine("=================================");
        Console.WriteLine($"Contract Version: {manifest["contract_version"]}");
        Console.WriteLine($"Language Version: {manifest["language_version"]}");
        Console.WriteLine($"Vectors found: {vectors.Count}\n");

        int passed = 0;
        int failed = 0;

        foreach (var vecFile in vectors)
        {
            string vecPath = Path.Combine(baseDir, vecFile!.ToString());
            var vector = JsonNode.Parse(File.ReadAllText(vecPath))!;
            string id = vector["id"]!.ToString();
            string name = vector["name"]!.ToString();

            try
            {
                var schemaJson = JsonSerializer.Deserialize<Dictionary<string, Dictionary<string, string>>>(vector["context_schema"]!.ToJsonString())!;
                var context = ParseContext(vector["context"]!, schemaJson);
                string source = vector["source"]!.ToString();

                var tokens = new Lexer(source).Tokenize();
                var ast = new Parser(tokens).Parse();
                new SemanticAnalyzer(schemaJson).Analyze(ast);
                var decisions = new Evaluator(context).EvaluateRules(ast);

                var actualOutput = new JsonObject
                {
                    ["status"] = "ok",
                    ["decisions"] = new JsonArray()
                };

                foreach (var d in decisions)
                {
                    var actionsArr = new JsonArray();
                    foreach (var a in d.Actions)
                    {
                        actionsArr.Add(new JsonObject
                        {
                            ["type"] = a.ActionType,
                            ["value"] = a.Value ?? null
                        });
                    }

                    ((JsonArray)actualOutput["decisions"]!).Add(new JsonObject
                    {
                        ["rule_id"] = d.RuleId,
                        ["matched"] = d.Matched,
                        ["actions"] = actionsArr
                    });
                }

                if (JsonNode.DeepEquals(actualOutput, vector["expected"]))
                {
                    Console.WriteLine($"[{id}] PASS - {name}");
                    passed++;
                }
                else
                {
                    Console.WriteLine($"[{id}] FAIL (Mismatch) - {name}");
                    failed++;
                }
            }
            catch (LexerException ex) { HandleError(ex.Code, vector, id, name, ref passed, ref failed); }
            catch (ParserException ex) { HandleError(ex.Code, vector, id, name, ref passed, ref failed); }
            catch (SemanticException ex) { HandleError(ex.Code, vector, id, name, ref passed, ref failed); }
            catch (EvaluatorException ex) { HandleError(ex.Code, vector, id, name, ref passed, ref failed); }
            catch (Exception ex)
            {
                Console.WriteLine($"[{id}] FAIL (Crash) - {name}");
                Console.WriteLine($"  Exception: {ex.Message}");
                failed++;
            }
        }

        Console.WriteLine($"\n{passed} passed, {failed} failed out of {vectors.Count}.");
        if (failed == 0)
        {
            Console.WriteLine("\nCONFORMANCE PASS");
            return 0;
        }
        Console.WriteLine("\nCONFORMANCE FAIL");
        return 1;
    }

    private static void HandleError(string code, JsonNode vector, string id, string name, ref int passed, ref int failed)
    {
        var expected = vector["expected"]!;
        if (expected["status"]?.ToString() == "error" && expected["error_code"]?.ToString() == code)
        {
            Console.WriteLine($"[{id}] PASS - {name}");
            passed++;
        }
        else
        {
            Console.WriteLine($"[{id}] FAIL (Unexpected Error) - {name}");
            Console.WriteLine($"  Expected: {expected["error_code"]}");
            Console.WriteLine($"  Actual:   {code}");
            failed++;
        }
    }

    private static Dictionary<string, object?> ParseContext(JsonNode contextNode, Dictionary<string, Dictionary<string, string>> schema)
    {
        var dict = new Dictionary<string, object?>();
        var ctxEl = JsonSerializer.Deserialize<JsonElement>(contextNode.ToJsonString());

        foreach (var objProp in ctxEl.EnumerateObject())
        {
            var innerDict = new Dictionary<string, object?>();
            if (objProp.Value.ValueKind == JsonValueKind.Object)
            {
                foreach (var innerProp in objProp.Value.EnumerateObject())
                {
                    if (innerProp.Value.ValueKind == JsonValueKind.Null)
                    {
                        innerDict[innerProp.Name] = null;
                        continue;
                    }

                    string expectedType = schema[objProp.Name][innerProp.Name];
                    object? val = expectedType switch
                    {
                        "Integer" => innerProp.Value.GetInt32(),
                        "Decimal" => innerProp.Value.ValueKind == JsonValueKind.Number ? innerProp.Value.GetDecimal() : decimal.Parse(innerProp.Value.GetString()!),
                        "Boolean" => innerProp.Value.GetBoolean(),
                        "Date" => DateOnly.Parse(innerProp.Value.GetString()!),
                        "String" => innerProp.Value.GetString()!,
                        _ => throw new Exception($"Unknown schema type: {expectedType}")
                    };
                    innerDict[innerProp.Name] = val;
                }
            }
            dict[objProp.Name] = innerDict;
        }
        return dict;
    }
}
