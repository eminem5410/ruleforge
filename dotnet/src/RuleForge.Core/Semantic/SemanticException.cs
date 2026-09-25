namespace RuleForge.Core.Semantic;

public class SemanticException : Exception
{
    public string Code { get; }

    public SemanticException(string code, string message) : base($"{code} Semantic Error: {message}")
    {
        Code = code;
    }
}
