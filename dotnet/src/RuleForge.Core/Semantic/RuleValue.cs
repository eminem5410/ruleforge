namespace RuleForge.Core.Semantic;

public enum RuleValueType
{
    Null,
    Integer,
    Decimal,
    String,
    Boolean,
    Date
}

public readonly record struct RuleValue(RuleValueType Type, object? Value);
