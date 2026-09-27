using System.Globalization;
using RuleForge.Core.Syntax;
using RuleForge.Core.Semantic;
using RuleForge.Core.Lexing;

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

        if (expr is DateLiteralExpression dlit)
        {
            return new RuleValue(RuleValueType.Date, dlit.Value);
        }
        if (expr is LiteralExpression lit)
        {
            return lit.Type switch
            {
                TokenType.BOOLEAN => new RuleValue(RuleValueType.Boolean, lit.Value?.ToString() == "true"),
                TokenType.INTEGER => new RuleValue(RuleValueType.Integer, int.Parse(lit.Value?.ToString()!, CultureInfo.InvariantCulture)),
                TokenType.DECIMAL => new RuleValue(RuleValueType.Decimal, decimal.Parse(lit.Value?.ToString()!, CultureInfo.InvariantCulture)),
                TokenType.DATE => new RuleValue(RuleValueType.Date, DateOnly.Parse(lit.Value?.ToString()!, CultureInfo.InvariantCulture)),
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
        
        if (expr is ArrayLiteralExpression arrLit)
        {
            var elements = arrLit.Elements.Select(EvaluateNode).ToList();
            return new RuleValue(RuleValueType.Array, elements);
        }
        
        if (expr is ArrayIndexExpression arrIdx)
        {
            var arr = EvaluateNode(arrIdx.Array);
            CheckNull(arr, "ArrayIndex");
            if (arr.Type != RuleValueType.Array) throw new EvaluatorException("RF4002", "Cannot index non-array");
            
            var indexVal = EvaluateNode(arrIdx.Index);
            if (indexVal.Type != RuleValueType.Integer) throw new EvaluatorException("RF4002", "Array index must be integer");
            
            var list = (List<RuleValue>)arr.Value!;
            int index = (int)indexVal.Value!;
            if (index < 0 || index >= list.Count) throw new EvaluatorException("RF4002", $"Array index {index} out of bounds (0..{list.Count-1})");
            return list[index];
        }

        if (expr is FunctionCallExpression fc)
        {
            var args = fc.Arguments.Select(EvaluateNode).ToList();
            CheckNull(args[0], fc.Name); // Simplified null check for first arg
            
            return fc.Name.ToUpperInvariant() switch
            {
                "LENGTH" => GetLength(args),
                "CONTAINS" => GetContains(args),
                "STARTS_WITH" => new RuleValue(RuleValueType.Boolean, ((string)args[0].Value!).StartsWith((string)args[1].Value!)),
                "ENDS_WITH" => new RuleValue(RuleValueType.Boolean, ((string)args[0].Value!).EndsWith((string)args[1].Value!)),
                "ABS" => new RuleValue(args[0].Type, Math.Abs(Convert.ToDecimal(args[0].Value, CultureInfo.InvariantCulture))),
                "DATE_ADD" => new RuleValue(RuleValueType.Date, GetDate(args[0], "DATE_ADD").AddDays((int)args[1].Value!)),
                "DATE_DIFF" => new RuleValue(RuleValueType.Integer, GetDate(args[1], "DATE_DIFF").DayNumber - GetDate(args[0], "DATE_DIFF").DayNumber),
                "EXTRACT" => GetExtract(args[0], (string)args[1].Value!),
                _ => throw new EvaluatorException("RF4001", $"Unknown function {fc.Name}")
            };
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
                    if (Convert.ToDecimal(rightVal.Value, CultureInfo.InvariantCulture) == 0) throw new EvaluatorException("RF4001", "Division by zero");
                    return new RuleValue(RuleValueType.Decimal, Convert.ToDecimal(leftVal.Value, CultureInfo.InvariantCulture) / Convert.ToDecimal(rightVal.Value, CultureInfo.InvariantCulture));
            }
        }
        
        throw new EvaluatorException("RF4001", "Unknown AST node");
    }

    private RuleValue GetLength(List<RuleValue> args)
        {
            if (args[0].Type == RuleValueType.Array) return new RuleValue(RuleValueType.Integer, ((List<RuleValue>)args[0].Value!).Count);
            if (args[0].Type == RuleValueType.String) return new RuleValue(RuleValueType.Integer, ((string)args[0].Value!).Length);
            throw new EvaluatorException("RF4001", "LENGTH requires string or array");
        }

        private RuleValue GetContains(List<RuleValue> args)
        {
            if (args[0].Type == RuleValueType.Array)
            {
                var list = (List<RuleValue>)args[0].Value!;
                return new RuleValue(RuleValueType.Boolean, list.Any(e => Equals(e.Value, args[1].Value)));
            }
            if (args[0].Type == RuleValueType.String)
            {
                return new RuleValue(RuleValueType.Boolean, ((string)args[0].Value!).Contains((string)args[1].Value!));
            }
            throw new EvaluatorException("RF4001", "CONTAINS requires string or array");
        }

        private DateOnly GetDate(RuleValue val, string funcName)
        {
            if (val.Type == RuleValueType.Null) throw new EvaluatorException("RF4002", $"Cannot perform '{funcName}' on NULL");
            if (val.Type == RuleValueType.Date) return (DateOnly)val.Value!;
            if (val.Type == RuleValueType.String && DateOnly.TryParseExact((string)val.Value!, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var d)) return d;
            throw new EvaluatorException("RF4002", "Invalid date value");
        }

        private RuleValue GetExtract(RuleValue dateVal, string part)
        {
            var d = GetDate(dateVal, "EXTRACT");
            return part switch
            {
                "year" => new RuleValue(RuleValueType.Integer, d.Year),
                "month" => new RuleValue(RuleValueType.Integer, d.Month),
                "day" => new RuleValue(RuleValueType.Integer, d.Day),
                _ => throw new EvaluatorException("RF4001", "Invalid part for EXTRACT")
            };
        }

        private int Compare(RuleValue l, RuleValue r)
    {
        if (l.Type == RuleValueType.String && r.Type == RuleValueType.String) return string.Compare((string)l.Value!, (string)r.Value!, StringComparison.Ordinal);
        if (l.Type == RuleValueType.Date && r.Type == RuleValueType.Date) return ((DateOnly)l.Value!).CompareTo((DateOnly)r.Value!);
        return Convert.ToDecimal(l.Value, CultureInfo.InvariantCulture).CompareTo(Convert.ToDecimal(r.Value, CultureInfo.InvariantCulture));
    }

    private object Add(RuleValue l, RuleValue r) => l.Type == RuleValueType.String ? (string)l.Value! + (string)r.Value! : Convert.ToDecimal(l.Value, CultureInfo.InvariantCulture) + Convert.ToDecimal(r.Value, CultureInfo.InvariantCulture);
    private object Subtract(RuleValue l, RuleValue r) => Convert.ToDecimal(l.Value, CultureInfo.InvariantCulture) - Convert.ToDecimal(r.Value, CultureInfo.InvariantCulture);
    private object Multiply(RuleValue l, RuleValue r) => Convert.ToDecimal(l.Value, CultureInfo.InvariantCulture) * Convert.ToDecimal(r.Value, CultureInfo.InvariantCulture);

    private RuleValue ToRuleValue(object? val)
    {
        if (val == null) return new RuleValue(RuleValueType.Null, null);
        if (val is int i) return new RuleValue(RuleValueType.Integer, i);
        if (val is decimal d) return new RuleValue(RuleValueType.Decimal, d);
        if (val is bool b) return new RuleValue(RuleValueType.Boolean, b);
        if (val is string s) return new RuleValue(RuleValueType.String, s);
        if (val is DateOnly dt) return new RuleValue(RuleValueType.Date, dt);
        if (val is double db) return new RuleValue(RuleValueType.Decimal, Convert.ToDecimal(db, CultureInfo.InvariantCulture));
        if (val is List<object?> listObj)
        {
            var ruleList = listObj.Select(ToRuleValue).ToList();
            return new RuleValue(RuleValueType.Array, ruleList);
        }
        if (val is object[] objArr)
        {
            var ruleList = objArr.Select(ToRuleValue).ToList();
            return new RuleValue(RuleValueType.Array, ruleList);
        }
        return new RuleValue(RuleValueType.String, val.ToString());
    }
}
