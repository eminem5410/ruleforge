using RuleForge.Core.Syntax;
using RuleForge.Core.Semantic;

namespace RuleForge.Core.Evaluation;

public class Evaluator
{
    private readonly Dictionary<string, object?> _context;
    private int _stepCount;
    private const int MaxExecutionSteps = 10000;

    public Evaluator(Dictionary<string, object?> context)
    {
        _context = context;
    }

    public List<Decision> EvaluateRules(List<RuleNode> astList)
    {
        var decisions = new List<Decision>();
        foreach (var rule in astList)
        {
            decisions.Add(EvaluateRule(rule));
        }
        return decisions;
    }

    private Decision EvaluateRule(RuleNode node)
    {
        _stepCount = 0;
        bool conditionResult = EvaluateNode(node.WhenExpr) is { Type: RuleValueType.Boolean, Value: true };
        
        var actions = conditionResult ? node.ThenActions : (node.ElseActions.Count > 0 ? node.ElseActions : new List<ActionNode> { new ActionNode("NO_ACTION") });
        return new Decision(node.Name, 1, node.LanguageVersion, conditionResult, actions);
    }

    private void CheckNull(RuleValue val, string op)
    {
        if (val.Type == RuleValueType.Null) throw new EvaluatorException("RF4002", $"Cannot perform '{op}' on NULL. Use IS NULL / IS NOT NULL.");
    }

    private RuleValue EvaluateNode(Expression expr)
    {
        _stepCount++;
        if (_stepCount > MaxExecutionSteps) throw new EvaluatorException("RF5003", $"Security Limit: Execution exceeded {MaxExecutionSteps} steps");

        if (expr is LiteralExpression lit)
        {
            return lit.Type switch
            {
                TokenType.BOOLEAN => new RuleValue(RuleValueType.Boolean, lit.Value?.ToString() == "true"),
                TokenType.INTEGER => new RuleValue(RuleValueType.Integer, int.Parse(lit.Value?.ToString()!))
                TokenType.DECIMAL => new RuleValue(RuleValueType.Decimal, decimal.Parse(lit.Value?.ToString()!))
                TokenType.DATE => new RuleValue(RuleValueType.Date, DateOnly.Parse(lit.Value?.ToString()!))
                _ => new RuleValue(RuleValueType.String, lit.Value)
            };
        }
        
        if (expr is PropertyExpression prop)
        {
            if (_context.TryGetValue(prop.ObjectName, out var objVal) && objVal is Dictionary<string, object?> dict)
            {
                if (dict.TryGetValue(prop.PropertyName, out var val)) return ToRuleValue(val);
            }
            return new RuleValue(RuleValueType.Null, null);
        }
        
        if (expr is NullCheckExpression nc)
        {
            var val = EvaluateNode(nc.Left);
            bool result = nc.IsNot ? val.Type != RuleValueType.Null : val.Type == RuleValueType.Null;
            return new RuleValue(RuleValueType.Boolean, result);
        }
        
        if (expr is UnaryExpression un)
        {
            var val = EvaluateNode(un.Operand);
            if (un.Operator == "NOT")
            {
                CheckNull(val, "NOT");
                return new RuleValue(RuleValueType.Boolean, !(bool)val.Value!);
            }
        }
        
        if (expr is BinaryExpression bin)
        {
            if (bin.Operator == "AND")
            {
                var l = EvaluateNode(bin.Left);
                if (l.Type == RuleValueType.Boolean && !(bool)l.Value!) return new RuleValue(RuleValueType.Boolean, false);
                var r = EvaluateNode(bin.Right);
                return new RuleValue(RuleValueType.Boolean, (bool)r.Value!);
            }
            if (bin.Operator == "OR")
            {
                var l = EvaluateNode(bin.Left);
                if (l.Type == RuleValueType.Boolean && (bool)l.Value!) return new RuleValue(RuleValueType.Boolean, true);
                var r = EvaluateNode(bin.Right);
                return new RuleValue(RuleValueType.Boolean, (bool)r.Value!);
            }

            var leftVal = EvaluateNode(bin.Left);
            var rightVal = EvaluateNode(bin.Right);
            CheckNull(leftVal, bin.Operator);
            CheckNull(rightVal, bin.Operator);

            switch (bin.Operator)
            {
                case "==": return new RuleValue(RuleValueType.Boolean, Equals(leftVal.Value, rightVal.Value));
                case "!=": return new RuleValue(RuleValueType.Boolean, !Equals(leftVal.Value, rightVal.Value));
                case ">": return new RuleValue(RuleValueType.Boolean, Compare(leftVal, rightVal) > 0);
                case "<": return new RuleValue(RuleValueType.Boolean, Compare(leftVal, rightVal) < 0);
                case ">=": return new RuleValue(RuleValueType.Boolean, Compare(leftVal, rightVal) >= 0);
                case "<=": return new RuleValue(RuleValueType.Boolean, Compare(leftVal, rightVal) <= 0);
                case "+": return new RuleValue(leftVal.Type, Add(leftVal, rightVal));
                case "-": return new RuleValue(leftVal.Type, Subtract(leftVal, rightVal));
                case "*": return new RuleValue(leftVal.Type, Multiply(leftVal, rightVal));
                case "/":
                    if ((decimal)rightVal.Value! == 0) throw new EvaluatorException("RF4001", "Division by zero");
                    return new RuleValue(RuleValueType.Decimal, (decimal)leftVal.Value! / (decimal)rightVal.Value!);
            }
        }
        
        throw new EvaluatorException("RF4001", "Unknown AST node");
    }

    private int Compare(RuleValue l, RuleValue r)
    {
        if (l.Type == RuleValueType.String && r.Type == RuleValueType.String) return string.Compare((string)l.Value!, (string)r.Value!, StringComparison.Ordinal);
        if (l.Type == RuleValueType.Date && r.Type == RuleValueType.Date) return ((DateOnly)l.Value!).CompareTo((DateOnly)r.Value!);
        return Convert.ToDecimal(l.Value).CompareTo(Convert.ToDecimal(r.Value));
    }

    private object Add(RuleValue l, RuleValue r) => l.Type == RuleValueType.String ? (string)l.Value! + (string)r.Value! : Convert.ToDecimal(l.Value) + Convert.ToDecimal(r.Value);
    private object Subtract(RuleValue l, RuleValue r) => Convert.ToDecimal(l.Value) - Convert.ToDecimal(r.Value);
    private object Multiply(RuleValue l, RuleValue r) => Convert.ToDecimal(l.Value) * Convert.ToDecimal(r.Value);

    private RuleValue ToRuleValue(object? val)
    {
        if (val == null) return new RuleValue(RuleValueType.Null, null);
        if (val is int i) return new RuleValue(RuleValueType.Integer, i);
        if (val is decimal d) return new RuleValue(RuleValueType.Decimal, d);
        if (val is bool b) return new RuleValue(RuleValueType.Boolean, b);
        if (val is string s) return new RuleValue(RuleValueType.String, s);
        if (val is DateOnly dt) return new RuleValue(RuleValueType.Date, dt);
        return new RuleValue(RuleValueType.String, val.ToString());
    }
}
