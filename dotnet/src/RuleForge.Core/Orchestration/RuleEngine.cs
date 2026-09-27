using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using RuleForge.Core.Syntax;
using RuleForge.Core.Semantic;
using RuleForge.Core.Evaluation;

namespace RuleForge.Core.Orchestration;

public class AppliedPatch
{
    public string RuleName { get; set; } = "";
    public int RuleIndex { get; set; }
    public int PatchIndex { get; set; }
    public string Path { get; set; } = "";
    public object? OldValue { get; set; }
    public object? NewValue { get; set; }
}

public class RuleTraceEntry
{
    public string RuleName { get; set; } = "";
    public int RuleIndex { get; set; }
    public bool Matched { get; set; }
    public List<string> AppliedPatches { get; set; } = new();
    public List<string> Actions { get; set; } = new();
}

public class PipelineResult
{
    public List<Decision> Decisions { get; set; } = new();
    public List<AppliedPatch> AppliedPatches { get; set; } = new();
    public Dictionary<string, object?> FinalContext { get; set; } = new();
    public List<RuleTraceEntry>? Trace { get; set; }
}

public class RuleEngine
{
    private readonly List<RuleNode> _ast;
    private readonly Dictionary<string, Dictionary<string, string>> _schema;

    public RuleEngine(List<RuleNode> ast, Dictionary<string, Dictionary<string, string>> schema, bool useCompiler = false)
    {
        _ast = ast;
        _schema = schema;
    }

    private void NormalizeAndValidateContext(Dictionary<string, object?> context)
    {
        if (context == null) throw new EvaluatorException("RF4003", "Expected a JSON object, but got null.");
        
        foreach (var objKvp in _schema)
        {
            var objName = objKvp.Key;
            var props = objKvp.Value;
            
            if (context.TryGetValue(objName, out var objVal))
            {
                if (objVal == null) continue;
                if (objVal is not Dictionary<string, object?> objDict)
                    throw new EvaluatorException("RF4003", $"Expected object for '{objName}' but got {objVal.GetType().Name}.");

                foreach (var propKvp in props)
                {
                    var propName = propKvp.Key;
                    var propType = propKvp.Value;
                    
                    if (objDict.TryGetValue(propName, out var val) && val != null)
                    {
                        try
                        {
                            if (propType == "Integer")
                            {
                                if (val is decimal dec) val = (int)dec;
                                if (val is long l) val = (int)l;
                                if (val is not int) throw new Exception();
                                objDict[propName] = val; // Normalize to int
                            }
                            else if (propType == "Decimal")
                            {
                                if (val is double db) val = Convert.ToDecimal(db, CultureInfo.InvariantCulture);
                                if (val is int i) val = (decimal)i;
                                if (val is not decimal) throw new Exception();
                                objDict[propName] = val; // Normalize to decimal
                            }
                            else if (propType == "String")
                            {
                                if (val is not string) throw new Exception();
                            }
                            else if (propType == "Boolean")
                            {
                                if (val is not bool) throw new Exception();
                            }
                            else if (propType == "Date")
                            {
                                if (val is string s)
                                {
                                    if (DateOnly.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var d))
                                        val = d;
                                    else throw new Exception();
                                }
                                else if (val is not DateOnly) throw new Exception();
                                objDict[propName] = val; // Normalize to DateOnly
                            }
                            else if (propType.StartsWith("Array<"))
                            {
                                if (val is not List<object?> list) throw new Exception();
                                var innerType = propType.Substring(6, propType.Length - 7);
                                for (int i = 0; i < list.Count; i++)
                                {
                                    var item = list[i];
                                    if (item == null) continue;
                                    if (innerType == "Integer")
                                    {
                                        if (item is decimal idec) list[i] = (int)idec;
                                        if (item is long il) list[i] = (int)il;
                                        if (list[i] is not int) throw new Exception();
                                    }
                                    else if (innerType == "String" && list[i] is not string) throw new Exception();
                                }
                            }
                        }
                        catch
                        {
                            throw new EvaluatorException("RF4003", $"expected {propType} but got {val.GetType().Name}");
                        }
                    }
                }
            }
        }
    }

    public PipelineResult Execute(Dictionary<string, object?> context, bool trace = false)
    {
        new SemanticAnalyzer(_schema).Analyze(_ast);
        
        var workingContext = DeepCopyContext(context);
        NormalizeAndValidateContext(workingContext);
        
        var evaluator = new Evaluator(workingContext);
        
        var result = new PipelineResult();
        result.FinalContext = workingContext;
        List<RuleTraceEntry>? traceEntries = trace ? new List<RuleTraceEntry>() : null;
        
        for (int i = 0; i < _ast.Count; i++)
        {
            var rule = _ast[i];
            Decision decision;
            
            // If evaluation fails, the exception propagates up (halting the pipeline).
            // No patches are applied for this rule, preserving atomicity.
            decision = evaluator.EvaluateRule(rule);
            
            result.Decisions.Add(decision);
            
            var ruleAppliedPaths = new List<string>();
            var ruleActions = decision.Actions.Select(a => a.ActionType).ToList();

            if (decision.Matched)
            {
                int patchIndex = 0;
                var patchesToApply = new List<(string Path, object? Value)>();
                
                foreach (var action in decision.Actions)
                {
                    if (action.ActionType == "SET")
                    {
                        patchesToApply.Add((action.Value!, action.Payload));
                    }
                }
                
                foreach (var (path, newValue) in patchesToApply)
                {
                    var parts = path.Split('.');
                    var objName = parts[0];
                    var propName = parts[1];
                    
                    object? oldValue = null;
                    if (workingContext.TryGetValue(objName, out var objVal) && objVal is Dictionary<string, object?> dict)
                    {
                        dict.TryGetValue(propName, out oldValue);
                    }
                    else
                    {
                        workingContext[objName] = new Dictionary<string, object?>();
                    }
                    
                    ((Dictionary<string, object?>)workingContext[objName]!)[propName] = newValue;
                    
                    ruleAppliedPaths.Add(path);
                    result.AppliedPatches.Add(new AppliedPatch
                    {
                        RuleName = rule.Name,
                        RuleIndex = i,
                        PatchIndex = patchIndex++,
                        Path = path,
                        OldValue = oldValue,
                        NewValue = newValue
                    });
                }
            }

            if (trace)
            {
                traceEntries!.Add(new RuleTraceEntry
                {
                    RuleName = rule.Name,
                    RuleIndex = i,
                    Matched = decision.Matched,
                    AppliedPatches = ruleAppliedPaths,
                    Actions = ruleActions
                });
            }
        }
        
        result.Trace = traceEntries;
        return result;
    }
    
    private Dictionary<string, object?> DeepCopyContext(Dictionary<string, object?> original)
    {
        var json = JsonSerializer.Serialize(original);
        var doc = JsonDocument.Parse(json);
        return DeserializeContext(doc.RootElement);
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
