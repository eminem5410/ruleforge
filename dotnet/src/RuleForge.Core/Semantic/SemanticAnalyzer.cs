using RuleForge.Core.Syntax;
using RuleForge.Core.Lexing;

namespace RuleForge.Core.Semantic;

public class SemanticAnalyzer
{
    private readonly Dictionary<string, Dictionary<string, string>> _schema;

    public SemanticAnalyzer(Dictionary<string, Dictionary<string, string>> schema)
    {
        _schema = schema;
    }

    public void Analyze(List<RuleNode> ast)
    {
        foreach (var rule in ast)
        {
            CheckActions(rule.ThenActions);
            CheckActions(rule.ElseActions);
            
            int depth = 0, count = 0;
            CheckAstLimits(rule.WhenExpr, 1, ref depth, ref count);
            if (depth > 50) throw new SemanticException("RF5001", $"Security Limit: AST depth {depth} exceeds maximum of 50");
            if (count > 500) throw new SemanticException("RF5002", $"Security Limit: AST node count {count} exceeds maximum of 500");

            var exprType = CheckNode(rule.WhenExpr);
            if (exprType != "Boolean")
                throw new SemanticException("RF3002", $"WHEN condition must evaluate to Boolean, got {exprType}");
        }
    }

    private void CheckAstLimits(Expression expr, int currentDepth, ref int maxDepth, ref int count)
    {
        count++;
        if (currentDepth > maxDepth) maxDepth = currentDepth;

        if (expr is BinaryExpression bin)
        {
            CheckAstLimits(bin.Left, currentDepth + 1, ref maxDepth, ref count);
            CheckAstLimits(bin.Right, currentDepth + 1, ref maxDepth, ref count);
        }
        else if (expr is UnaryExpression un)
        {
            CheckAstLimits(un.Operand, currentDepth + 1, ref maxDepth, ref count);
        }
        else if (expr is NullCheckExpression nc)
        {
            CheckAstLimits(nc.Left, currentDepth + 1, ref maxDepth, ref count);
        }
    }

    private void CheckActions(List<ActionNode> actions)
    {
        int terminalCount = actions.Count(a => a.ActionType == "ALLOW" || a.ActionType == "DENY" || a.ActionType == "NO_ACTION");
        if (terminalCount > 1)
            throw new SemanticException("RF3002", "A block can have at most ONE terminal decision");
    }

    private string CheckNode(Expression expr)
    {
        if (expr is LiteralExpression lit)
        {
            return lit.Type switch
            {
                TokenType.INTEGER => "Integer",
                TokenType.DECIMAL => "Decimal",
                TokenType.STRING => "String",
                TokenType.BOOLEAN => "Boolean",
                TokenType.DATE => "Date",
                _ => "Unknown"
            };
        }
        if (expr is PropertyExpression prop)
        {
            if (!_schema.TryGetValue(prop.ObjectName, out var props))
                throw new SemanticException("RF3002", $"Context object '{prop.ObjectName}' not defined");
            if (!props.TryGetValue(prop.PropertyName, out var type))
                throw new SemanticException("RF3002", $"Property '{prop.PropertyName}' not found in '{prop.ObjectName}'");
            return type;
        }
        if (expr is NullCheckExpression)
        {
            return "Boolean";
        }
        if (expr is UnaryExpression un)
        {
            if (un.Operator == "NOT")
            {
                if (CheckNode(un.Operand) != "Boolean")
                    throw new SemanticException("RF3001", "Operator 'NOT' requires Boolean");
                return "Boolean";
            }
        }
        if (expr is BinaryExpression bin)
        {
            var l = CheckNode(bin.Left);
            var r = CheckNode(bin.Right);
            var op = bin.Operator;

            var validNumerics = new[] { "Integer", "Decimal" };
            var validComparison = new[] { "Integer", "Decimal", "Date" };

            if (op == "AND" || op == "OR")
            {
                if (l != "Boolean" || r != "Boolean")
                    throw new SemanticException("RF3001", $"Operator '{op}' requires Boolean operands");
                return "Boolean";
            }
            if (op == "==" || op == "!=")
            {
                if (l != r)
                    throw new SemanticException("RF3001", $"Cannot compare {l} with {r}");
                return "Boolean";
            }
            if (op == ">" || op == "<" || op == ">=" || op == "<=")
            {
                if (!validComparison.Contains(l) || !validComparison.Contains(r))
                    throw new SemanticException("RF3001", $"Operator '{op}' requires numeric/date");
                return "Boolean";
            }
            if (op == "+" || op == "-" || op == "*" || op == "/")
            {
                if (!validNumerics.Contains(l) || !validNumerics.Contains(r))
                    throw new SemanticException("RF3001", $"Operator '{op}' requires numeric");
                return l == "Decimal" || r == "Decimal" ? "Decimal" : "Integer";
            }
        }
        throw new SemanticException("RF3003", "Unknown AST node");
    }
}
