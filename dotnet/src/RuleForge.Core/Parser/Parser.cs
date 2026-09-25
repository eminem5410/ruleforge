using RuleForge.Core.Lexing;
using RuleForge.Core.Syntax;

namespace RuleForge.Core.Parser;

public class Parser
{
    private readonly List<Token> _tokens;
    private int _pos;
    private Token CurrentToken => _tokens[_pos];

    public Parser(List<Token> tokens)
    {
        _tokens = tokens;
        _pos = 0;
    }

    private void Advance() => _pos++;
    
    private Token Expect(TokenType type)
    {
        if (CurrentToken.Type == type)
        {
            var t = CurrentToken;
            Advance();
            return t;
        }
        throw new ParserException("RF2002", $"Expected {type} but got {CurrentToken.Type} ('{CurrentToken.Value}')", CurrentToken.Line, CurrentToken.Column);
    }

    public List<RuleNode> Parse()
    {
        var rules = new List<RuleNode>();
        while (CurrentToken.Type != TokenType.EOF)
        {
            rules.Add(ParseRule());
        }
        return rules;
    }

    private RuleNode ParseRule()
    {
        Expect(TokenType.RULE);
        var name = CurrentToken.Value;
        Expect(TokenType.IDENTIFIER);
        
        Expect(TokenType.LANGUAGE);
        if (!int.TryParse(CurrentToken.Value, out int langVer))
            throw new ParserException("RF2002", "Expected integer for language version", CurrentToken.Line, CurrentToken.Column);
        Expect(TokenType.INTEGER);
        
        Expect(TokenType.WHEN);
        var whenExpr = Expression();
        
        Expect(TokenType.THEN);
        var thenActions = ActionList();
        
        var elseActions = new List<ActionNode>();
        if (CurrentToken.Type == TokenType.ELSE)
        {
            Advance();
            elseActions = ActionList();
        }
        
        Expect(TokenType.END);
        return new RuleNode(name, langVer, whenExpr, thenActions, elseActions);
    }

    private List<ActionNode> ActionList()
    {
        var actions = new List<ActionNode>();
        actions.Add(ParseAction());
        
        while (CurrentToken.Type == TokenType.ALLOW || CurrentToken.Type == TokenType.DENY || 
               CurrentToken.Type == TokenType.ALERT || CurrentToken.Type == TokenType.APPLY || 
               CurrentToken.Type == TokenType.NO_ACTION)
        {
            actions.Add(ParseAction());
        }
        return actions;
    }

    private ActionNode ParseAction()
    {
        var t = CurrentToken;
        if (t.Type == TokenType.ALLOW || t.Type == TokenType.NO_ACTION)
        {
            Advance();
            return new ActionNode(t.Value);
        }
        if (t.Type == TokenType.DENY || t.Type == TokenType.ALERT || t.Type == TokenType.APPLY)
        {
            Advance();
            var valToken = CurrentToken;
            Expect(TokenType.STRING);
            return new ActionNode(t.Value, valToken.Value);
        }
        throw new ParserException("RF2005", $"Expected action but got {t.Type}", t.Line, t.Column);
    }

    private Expression Expression() => LogicalOr();

    private Expression LogicalOr()
    {
        var node = LogicalAnd();
        while (CurrentToken.Type == TokenType.OR)
        {
            var op = CurrentToken.Value;
            Advance();
            node = new BinaryExpression(node, op, LogicalAnd());
        }
        return node;
    }

    private Expression LogicalAnd()
    {
        var node = LogicalNot();
        while (CurrentToken.Type == TokenType.AND)
        {
            var op = CurrentToken.Value;
            Advance();
            node = new BinaryExpression(node, op, LogicalNot());
        }
        return node;
    }

    private Expression LogicalNot()
    {
        if (CurrentToken.Type == TokenType.NOT)
        {
            Advance();
            return new UnaryExpression("NOT", LogicalNot());
        }
        return Comparison();
    }

    private Expression Comparison()
    {
        var node = Arithmetic();
        
        if (CurrentToken.Type == TokenType.IS)
        {
            Advance();
            bool isNot = false;
            if (CurrentToken.Type == TokenType.NOT)
            {
                Advance();
                isNot = true;
            }
            Expect(TokenType.NULL);
            return new NullCheckExpression(node, isNot);
        }
        
        var compTypes = new[] { TokenType.EQ, TokenType.NEQ, TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE };
        if (compTypes.Contains(CurrentToken.Type))
        {
            var op = CurrentToken.Value;
            Advance();
            return new BinaryExpression(node, op, Arithmetic());
        }
        return node;
    }

    private Expression Arithmetic()
    {
        var node = Term();
        while (CurrentToken.Type == TokenType.PLUS || CurrentToken.Type == TokenType.MINUS)
        {
            var op = CurrentToken.Value;
            Advance();
            node = new BinaryExpression(node, op, Term());
        }
        return node;
    }

    private Expression Term()
    {
        var node = Factor();
        while (CurrentToken.Type == TokenType.MULTIPLY || CurrentToken.Type == TokenType.DIVIDE)
        {
            var op = CurrentToken.Value;
            Advance();
            node = new BinaryExpression(node, op, Factor());
        }
        return node;
    }

    private Expression Factor()
    {
        var t = CurrentToken;
        if (t.Type == TokenType.LPAREN)
        {
            Advance();
            var expr = Expression();
            Expect(TokenType.RPAREN);
            return expr;
        }
        if (t.Type == TokenType.INTEGER || t.Type == TokenType.DECIMAL || 
            t.Type == TokenType.STRING || t.Type == TokenType.BOOLEAN || t.Type == TokenType.DATE)
        {
            Advance();
            return new LiteralExpression(t.Value, t.Type);
        }
        if (t.Type == TokenType.IDENTIFIER)
        {
            var name = t.Value;
            Advance();
            if (CurrentToken.Type == TokenType.DOT)
            {
                Advance();
                var propToken = CurrentToken;
                Expect(TokenType.IDENTIFIER);
                return new PropertyExpression(name, propToken.Value);
            }
            return new LiteralExpression(name, t.Type);
        }
        throw new ParserException("RF2004", $"Invalid expression, unexpected token {t.Type}", t.Line, t.Column);
    }
}
