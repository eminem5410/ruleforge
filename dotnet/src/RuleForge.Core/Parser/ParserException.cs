namespace RuleForge.Core.Parser;

public class ParserException : Exception
{
    public string Code { get; }
    public int Line { get; }
    public int Column { get; }

    public ParserException(string code, string message, int line, int column) 
        : base($"{code} Parse Error: {message} at Line {line}, Column {column}")
    {
        Code = code;
        Line = line;
        Column = column;
    }
}
