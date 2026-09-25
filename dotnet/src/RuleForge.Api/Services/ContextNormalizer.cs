using System.Collections.Generic;
using System.Text.Json;

namespace RuleForge.Api.Services;

public static class ContextNormalizer
{
    public static Dictionary<string, object?> Normalize(Dictionary<string, object?> context, Dictionary<string, Dictionary<string, string>> schema)
    {
        var result = new Dictionary<string, object?>();
        
        foreach (var kvp in context)
        {
            if (kvp.Value is JsonElement el && el.ValueKind == JsonValueKind.Object)
            {
                var innerDict = new Dictionary<string, object?>();
                foreach (var prop in el.EnumerateObject())
                {
                    if (schema.TryGetValue(kvp.Key, out var props) && props.TryGetValue(prop.Name, out var type))
                    {
                        innerDict[prop.Name] = type switch
                        {
                            "Integer" => prop.Value.GetInt32(),
                            "Decimal" => prop.Value.GetDecimal(),
                            "Boolean" => prop.Value.GetBoolean(),
                            "Date" => DateOnly.Parse(prop.Value.GetString()!),
                            "String" => prop.Value.GetString()!,
                            _ => null
                        };
                    }
                }
                result[kvp.Key] = innerDict;
            }
            else
            {
                result[kvp.Key] = kvp.Value;
            }
        }
        return result;
    }
}
