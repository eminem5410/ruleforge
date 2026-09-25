using System.Text.RegularExpressions;

namespace RuleForge.Core.Lexing;

public class Lexer
{
    private readonly string _source;
    private int _pos;
    private int _line;
    private int _column;
    private char? _currentChar;

    private static readonly Dictionary<string, TokenType> Keywords = new()
    {
        { "RULE", TokenType.RULE }, { "LANGUAGE", TokenType.LANGUAGE },
        { "WHEN", TokenType.WHEN }, { "THEN", TokenType.THEN },
        { "ELSE", TokenType.ELSE }, { "END", TokenType.END },
        { "ALLOW", TokenType.ALLOW }, { "DENY", TokenType.DENY },
        { "NO_ACTION", TokenType.NO_ACTION }, { "ALERT", TokenType.ALERT },
        { "APPLY", TokenType.APPLY }, { "AND", TokenType.AND },
        { "OR", TokenType.OR }, { "NOT", TokenType.NOT },
        { "IS", TokenType.IS }, { "NULL", TokenType.NULL },
        { "true", TokenType.BOOLEAN }, { "false", TokenType.BOOLEAN }
    };

    private static readonly Regex DateRegex = new(@"\d{4}-\d{2}-\d{2}", RegexOptions.Compiled);

    public Lexer(string source)
    {
        _source = source;
        _pos = 0;
        _line = 1;
        _column = 1;
        _currentChar = _source.Length > 0 ? _source[0] : null;
    }

    private void Advance()
    {
        if (_currentChar == '\n')
        {
            _line++;
            _column = 1;
        }
        else
        {
            _column++;
        }
        _pos++;
        _currentChar = _pos < _source.Length ? _source[_pos] : null;
    }

    private void SkipWhitespace()
    {
        while (_currentChar.HasValue && char.IsWhiteSpace(_currentChar.Value))
        {
            Advance();
        }
    }

    private Token ReadString()
    {
        int startLine = _line, startCol = _column;
        Advance(); // Skip opening quote
        string value = "";
        
        while (_currentChar.HasValue && _currentChar != '"')
        {
            value += _currentChar;
            Advance();
        }
        
        if (!_currentChar.HasValue)
        {
            throw new LexerException("RF1001", "Unterminated string", startLine, startCol);
        }
        
        Advance(); // Skip closing quote
        return new Token(TokenType.STRING, value, startLine, startCol);
    }

    private Token ReadNumber()
    {
        int startLine = _line, startCol = _column;
        
        var match = DateRegex.Match(_source, _pos);
        if (match.Success && match.Index == _pos)
        {
            string dateStr = match.Value;
            for (int i = 0; i < dateStr.Length; i++) Advance();
            return new Token(TokenType.DATE, dateStr, startLine, startCol);
        }

        string val = "";
        bool isDecimal = false;
        
        while (_currentChar.HasValue && (char.IsDigit(_currentChar.Value) || _currentChar == '.'))
        {
            if (_currentChar == '.')
            {
                if (isDecimal) throw new LexerException("RF1001", "Invalid number format", startLine, startCol);
                isDecimal = true;
            }
            val += _currentChar;
            Advance();
        }
        
        return new Token(isDecimal ? TokenType.DECIMAL : TokenType.INTEGER, val, startLine, startCol);
    }

    private Token ReadIdentifier()
    {
        int startLine = _line, startCol = _column;
        string val = "";
        
        while (_currentChar.HasValue && (char.IsLetterOrDigit(_currentChar.Value) || _currentChar == '_'))
        {
            val += _currentChar;
            Advance();
        }
        
        TokenType type = Keywords.TryGetValue(val, out var kwType) ? kwType : TokenType.IDENTIFIER;
        return new Token(type, val, startLine, startCol);
    }

    public List<Token> Tokenize()
    {
        var tokens = new List<Token>();
        
        while (_currentChar.HasValue)
        {
            if (char.IsWhiteSpace(_currentChar.Value))
            {
                SkipWhitespace();
                continue;
            }

            if (_currentChar == '/' && _pos + 1 < _source.Length && _source[_pos + 1] == '/')
            {
                while (_currentChar.HasValue && _currentChar != '\n') Advance();
                continue;
            }

            int startLine = _line, startCol = _column;

            if (_currentChar == '"') { tokens.Add(ReadString()); continue; }
            if (char.IsDigit(_currentChar.Value)) { tokens.Add(ReadNumber()); continue; }
            if (char.IsLetter(_currentChar.Value) || _currentChar == '_') { tokens.Add(ReadIdentifier()); continue; }
            
            if (_currentChar == '=' && _pos + 1 < _source.Length && _source[_pos + 1] == '=') { tokens.Add(new Token(TokenType.EQ, "==", startLine, startCol)); Advance(); Advance(); continue; }
            if (_currentChar == '!' && _pos + 1 < _source.Length && _source[_pos + 1] == '=') { tokens.Add(new Token(TokenType.NEQ, "!=", startLine, startCol)); Advance(); Advance(); continue; }
            if (_currentChar == '>' && _pos + 1 < _source.Length && _source[_pos + 1] == '=') { tokens.Add(new Token(TokenType.GTE, ">=", startLine, startCol)); Advance(); Advance(); continue; }
            if (_currentChar == '<' && _pos + 1 < _source.Length && _source[_pos + 1] == '=') { tokens.Add(new Token(TokenType.LTE, "<=", startLine, startCol)); Advance(); Advance(); continue; }

            switch (_currentChar)
            {
                case '>': tokens.Add(new Token(TokenType.GT, ">", startLine, startCol)); Advance(); break;
                case '<': tokens.Add(new Token(TokenType.LT, "<", startLine, startCol)); Advance(); break;
                case '+': tokens.Add(new Token(TokenType.PLUS, "+", startLine, startCol)); Advance(); break;
                case '-': tokens.Add(new Token(TokenType.MINUS, "-", startLine, startCol)); Advance(); break;
                case '*': tokens.Add(new Token(TokenType.MULTIPLY, "*", startLine, startCol)); Advance(); break;
                case '/': tokens.Add(new Token(TokenType.DIVIDE, "/", startLine, startCol)); Advance(); break;
                case '(': tokens.Add(new Token(TokenType.LPAREN, "(", startLine, startCol)); Advance(); break;
                case ')': tokens.Add(new Token(TokenType.RPAREN, ")", startLine, startCol)); Advance(); break;
                case '.': tokens.Add(new Token(TokenType.DOT, ".", startLine, startCol)); Advance(); break;
                case ',': tokens.Add(new Token(TokenType.COMMA, ",", startLine, startCol)); Advance(); break;
                default: throw new LexerException("RF1001", $"Unexpected character '{_currentChar}'", startLine, startCol);
            }
        }
        
        tokens.Add(new Token(TokenType.EOF, "", _line, _column));
        return tokens;
    }
}
