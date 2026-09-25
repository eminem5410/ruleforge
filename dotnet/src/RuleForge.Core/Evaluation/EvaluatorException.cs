namespace RuleForge.Core.Evaluation;

public class EvaluatorException : Exception
{
    public string Code { get; }
    public EvaluatorException(string code, string message) : base($"{code} Runtime Error: {message}")
    {
        Code = code;
    }
}
