using System.Globalization;
using System.Linq;
using RuleForge.Core.Syntax;
using RuleForge.Core.Semantic;
using RuleForge.Core.Lexing;

namespace RuleForge.Core.Evaluation;

public class Evaluator
{
    private readonly Dictionary<string, object?> _context;
    private int _stepCount;
    private const int MaxExecutionSteps = 10000;
    private readonly bool _deepTrace;
    private bool _traceEnabled;
    private TraceNode? _errorTrace;

    public TraceNode? LastTrace { get; private set; }

    public Evaluator(Dictionary<string, object?> context, bool deepTrace = false)
    {
        _context = context;
        _deepTrace = deepTrace;
    }

    private sealed record EvalResult(RuleValue Value, TraceNode? Trace);

    // === Public API ===

    public List<Decision> EvaluateRules(List<RuleNode> astList)
    {
        var decisions = new List<Decision>();
        foreach (var rule in astList)
        {
            decisions.Add(EvaluateRule(rule));
        }
        return decisions;
    }

    public Decision BuildDecision(RuleNode node, bool matched, List<ActionNode> actions)
    {
        return new Decision(node.Name, 1, node.LanguageVersion, matched, actions);
    }

    public Decision EvaluateRule(RuleNode node)
    {
        _stepCount = 0;
        LastTrace = null;
        _errorTrace = null;

        _traceEnabled = _deepTrace;
        EvalResult condResult;
        try
        {
            if (node.MatchNode != null)
            {
                var matchRes = EvaluateNodeInternal(node.MatchNode.MatchExpression);
                
                bool matched = true;
                bool caseMatched = false;
                var matchRawActions = new List<ActionNode> { new ActionNode("NO_ACTION") };
                var caseTraces = new List<TraceNode>();
                
                foreach (var caseNode in node.MatchNode.Cases)
                {
                    if (caseMatched)
                    {
                        if (_traceEnabled)
                        {
                            caseTraces.Add(new TraceNode { NodeType = "Case", Value = null, Type = "Null", Children = new List<TraceNode>(), ShortCircuited = true, Reason = "short_circuit" });
                        }
                    }
                    else
                    {
                        var caseRes = EvaluateNodeInternal(caseNode.Value);
                        bool isMatch = (matchRes.Value.Type == caseRes.Value.Type && object.Equals(matchRes.Value.Value, caseRes.Value.Value));
                        
                        if (_traceEnabled)
                        {
                            caseTraces.Add(new TraceNode { NodeType = "Case", Value = SerializeTraceValue(caseRes.Value), Type = GetTypeName(caseRes.Value), Children = new List<TraceNode>(), ShortCircuited = false, Matched = isMatch });
                        }
                        
                        if (isMatch)
                        {
                            caseMatched = true;
                            matchRawActions = caseNode.Actions;
                        }
                    }
                }
                
                if (!caseMatched)
                {
                    if (node.MatchNode.DefaultActions != null && node.MatchNode.DefaultActions.Count > 0)
                    {
                        matchRawActions = node.MatchNode.DefaultActions;
                    }
                    else
                    {
                        matchRawActions = new List<ActionNode> { new ActionNode("NO_ACTION") };
                    }
                }
                
                var matchResolvedActions = new List<ActionNode>();
                foreach (var matchAction in matchRawActions)
                {
                    if (matchAction is SetActionNode setAct)
                    {
                        var val = EvaluateNode(setAct.ValueExpr);
                        matchResolvedActions.Add(new ActionNode("SET", setAct.Path, UnwrapRuleValue(val)));
                    }
                    else if (matchAction is EmitActionNode emit)
                    {
                        object? payload = null;
                        if (emit.PayloadPath != null)
                        {
                            var payloadVal = EvaluateNode(emit.PayloadPath);
                            payload = UnwrapRuleValue(payloadVal);
                        }
                        matchResolvedActions.Add(new ActionNode("EMIT", emit.IntentName, payload));
                    }
                    else
                    {
                        matchResolvedActions.Add(matchAction);
                    }
                }
                
                if (_traceEnabled)
                {
                    TraceNode? defaultTrace = null;
                    if (node.MatchNode.DefaultActions != null)
                    {
                        defaultTrace = new TraceNode { NodeType = "Default", Value = null, Type = "Null", Children = new List<TraceNode>(), ShortCircuited = caseMatched, Matched = !caseMatched };
                    }
                    
                    var rootMatchTrace = new TraceNode
                    {
                        NodeType = "MatchExpression",
                        Value = SerializeTraceValue(matchRes.Value),
                        Type = GetTypeName(matchRes.Value),
                        Children = caseTraces,
                        ShortCircuited = false
                    };
                    if (defaultTrace != null) rootMatchTrace.Children.Add(defaultTrace);
                    
                    LastTrace = rootMatchTrace;
                }
                
                return new Decision(node.Name, 1, node.LanguageVersion, matched, matchResolvedActions);
            }
            condResult = EvaluateNodeInternal(node.WhenExpr!);
        }
        catch (EvaluatorException)
        {
            LastTrace = _errorTrace;
            throw;
        }

        bool conditionResult = condResult.Value is { Type: RuleValueType.Boolean, Value: true };

        if (_deepTrace)
        {
            LastTrace = condResult.Trace;
        }
        _traceEnabled = false;

        var rawActions = conditionResult ? node.ThenActions : (node.ElseActions.Count > 0 ? node.ElseActions : new List<ActionNode> { new ActionNode("NO_ACTION") });
        var actions = new List<ActionNode>();
        foreach (var a in rawActions)
        {
            if (a is SetActionNode setAct)
            {
                var val = EvaluateNode(setAct.ValueExpr);
                actions.Add(new ActionNode("SET", setAct.Path, UnwrapRuleValue(val)));
            }
            else if (a is EmitActionNode emit)
            {
                object? payload = null;
                if (emit.PayloadPath != null)
                {
                    var payloadVal = EvaluateNode(emit.PayloadPath);
                    payload = UnwrapRuleValue(payloadVal);
                }
                actions.Add(new ActionNode("EMIT", emit.IntentName, payload));
            }
            else
            {
                actions.Add(a);
            }
        }
        return new Decision(node.Name, 1, node.LanguageVersion, conditionResult, actions);
    }

    public RuleValue EvaluateNode(Expression expr)
    {
        return EvaluateNodeInternal(expr).Value;
    }

    // === V11.2 Trace Helpers ===

    private static string GetNodeType(Expression expr)
    {
        return expr switch
        {
            BinaryExpression => "BinaryExpression",
            UnaryExpression => "UnaryExpression",
            NullCheckExpression => "NullCheck",
            LiteralExpression => "Literal",
            PropertyExpression => "PropertyExpression",
            FunctionCallExpression => "FunctionCall",
            ArrayLiteralExpression => "ArrayLiteral",
            ArrayIndexExpression => "ArrayIndex",
            DateLiteralExpression => "DateLiteral",
            AnyAllExpression => "AnyAll",
            FilterMapExpression => "FilterMap",
            _ => throw new EvaluatorException("RF5004", $"V11.2: Unmapped AST node type: {expr.GetType().Name}")
        };
    }

    private static string GetTypeName(RuleValue val)
    {
        return val.Type switch
        {
            RuleValueType.Boolean => "Boolean",
            RuleValueType.Integer => "Integer",
            RuleValueType.Decimal => "Decimal",
            RuleValueType.String => "String",
            RuleValueType.Date => "Date",
            RuleValueType.Null => "Null",
            RuleValueType.Array => "Array",
            RuleValueType.Object => "Object",
            _ => "Unknown"
        };
    }

    private static object? SerializeTraceValue(RuleValue val)
    {
        if (val.Type == RuleValueType.Null) return null;
        if (val.Type == RuleValueType.Date) return ((DateOnly)val.Value!).ToString("yyyy-MM-dd");
        if (val.Type == RuleValueType.Decimal && val.Value is decimal decimalValue)
            return decimalValue.ToString(CultureInfo.InvariantCulture);
        if (val.Type == RuleValueType.Array && val.Value is List<RuleValue> list)
        {
            return list.Select(SerializeTraceValue).ToList();
        }
        return val.Value;
    }

    private TraceNode? BuildTrace(Expression expr, RuleValue val, string? op = null,
        List<TraceNode>? children = null, bool shortCircuited = false, EvaluatorException? error = null)
    {
        if (!_traceEnabled) return null;
        return new TraceNode
        {
            NodeType = GetNodeType(expr),
            Operator = op,
            Value = shortCircuited ? null : SerializeTraceValue(val),
            Type = shortCircuited ? "Null" : GetTypeName(val),
            Children = children ?? new List<TraceNode>(),
            ShortCircuited = shortCircuited,
            ErrorCode = error?.Code,
            ErrorMessage = error?.Message
        };
    }

    private TraceNode? BuildPhantom(Expression expr)
    {
        if (!_traceEnabled) return null;
        return new TraceNode
        {
            NodeType = GetNodeType(expr),
            Value = null,
            Type = "Null",
            Children = new List<TraceNode>(),
            ShortCircuited = true
        };
    }

    private List<TraceNode> T(params TraceNode?[] traces)
    {
        return traces.Where(t => t != null).Select(t => t!).ToList();
    }

    // === Internal Evaluation ===

    private EvalResult EvaluateNodeInternal(Expression expr)
    {
        _stepCount++;
        if (_stepCount > MaxExecutionSteps)
            throw new EvaluatorException("RF5003", $"Security Limit: Execution exceeded {MaxExecutionSteps} steps");

        try
        {
            if (expr is DateLiteralExpression dlit)
            {
                var value = new RuleValue(RuleValueType.Date, dlit.Value);
                return new EvalResult(value, BuildTrace(expr, value));
            }

            if (expr is LiteralExpression lit)
            {
                RuleValue value;
                if (lit.Value?.ToString() == "it" && _context.ContainsKey("it"))
                {
                    value = ToRuleValue(_context["it"]);
                }
                else
                {
                    value = lit.Type switch
                    {
                        TokenType.BOOLEAN => new RuleValue(RuleValueType.Boolean, lit.Value?.ToString() == "true"),
                        TokenType.INTEGER => new RuleValue(RuleValueType.Integer, int.Parse(lit.Value?.ToString()!, CultureInfo.InvariantCulture)),
                        TokenType.DECIMAL => new RuleValue(RuleValueType.Decimal, decimal.Parse(lit.Value?.ToString()!, CultureInfo.InvariantCulture)),
                        TokenType.DATE => new RuleValue(RuleValueType.Date, DateOnly.Parse(lit.Value?.ToString()!, CultureInfo.InvariantCulture)),
                        _ => new RuleValue(RuleValueType.String, lit.Value)
                    };
                }
                return new EvalResult(value, BuildTrace(expr, value));
            }

            if (expr is PropertyExpression prop)
            {
                RuleValue value;
                if (prop.ObjectName == "it" && _context.ContainsKey("it"))
                {
                    var itVal = _context["it"];
                    if (itVal is Dictionary<string, object?> itDict && itDict.TryGetValue(prop.PropertyName, out var val))
                    {
                        value = ToRuleValue(val);
                    }
                    else
                    {
                        value = new RuleValue(RuleValueType.Null, null);
                    }
                }
                else if (_context.TryGetValue(prop.ObjectName, out var objVal) && objVal is Dictionary<string, object?> dict)
                {
                    value = dict.TryGetValue(prop.PropertyName, out var val) ? ToRuleValue(val) : new RuleValue(RuleValueType.Null, null);
                }
                else
                {
                    value = new RuleValue(RuleValueType.Null, null);
                }
                return new EvalResult(value, BuildTrace(expr, value));
            }

            if (expr is NullCheckExpression nc)
            {
                var leftResult = EvaluateNodeInternal(nc.Left);
                bool result = nc.IsNot ? leftResult.Value.Type != RuleValueType.Null : leftResult.Value.Type == RuleValueType.Null;
                var value = new RuleValue(RuleValueType.Boolean, result);
                string opStr = nc.IsNot ? "IS NOT NULL" : "IS NULL";
                return new EvalResult(value, BuildTrace(expr, value, opStr, T(leftResult.Trace)));
            }

            if (expr is UnaryExpression un)
            {
                var operandResult = EvaluateNodeInternal(un.Operand);
                if (un.Operator == "NOT")
                {
                    CheckNull(operandResult.Value, "NOT");
                    var value = new RuleValue(RuleValueType.Boolean, !GetBool(operandResult.Value));
                    return new EvalResult(value, BuildTrace(expr, value, "NOT", T(operandResult.Trace)));
                }
                throw new EvaluatorException("RF4001", $"Unknown unary operator: {un.Operator}");
            }

            if (expr is BinaryExpression bin)
            {
                // AND with short-circuit
                if (bin.Operator == "AND")
                {
                    var leftResult = EvaluateNodeInternal(bin.Left);
                    if (leftResult.Value.Type == RuleValueType.Boolean && !GetBool(leftResult.Value))
                    {
                        var phantom = BuildPhantom(bin.Right);
                        var value = new RuleValue(RuleValueType.Boolean, false);
                        return new EvalResult(value, BuildTrace(expr, value, "AND", T(leftResult.Trace, phantom)));
                    }
                    var rightResult = EvaluateNodeInternal(bin.Right);
                    var result = new RuleValue(RuleValueType.Boolean, GetBool(rightResult.Value));
                    return new EvalResult(result, BuildTrace(expr, result, "AND", T(leftResult.Trace, rightResult.Trace)));
                }

                // OR with short-circuit
                if (bin.Operator == "OR")
                {
                    var leftResult = EvaluateNodeInternal(bin.Left);
                    if (leftResult.Value.Type == RuleValueType.Boolean && GetBool(leftResult.Value))
                    {
                        var phantom = BuildPhantom(bin.Right);
                        var value = new RuleValue(RuleValueType.Boolean, true);
                        return new EvalResult(value, BuildTrace(expr, value, "OR", T(leftResult.Trace, phantom)));
                    }
                    var rightResult = EvaluateNodeInternal(bin.Right);
                    var result = new RuleValue(RuleValueType.Boolean, GetBool(rightResult.Value));
                    return new EvalResult(result, BuildTrace(expr, result, "OR", T(leftResult.Trace, rightResult.Trace)));
                }

                // Other binary operators
                var leftVal = EvaluateNodeInternal(bin.Left);
                var rightVal = EvaluateNodeInternal(bin.Right);
                CheckNull(leftVal.Value, bin.Operator);
                CheckNull(rightVal.Value, bin.Operator);

                RuleValue res = bin.Operator switch
                {
                    "==" => new RuleValue(RuleValueType.Boolean, Equals(leftVal.Value.Value, rightVal.Value.Value)),
                    "!=" => new RuleValue(RuleValueType.Boolean, !Equals(leftVal.Value.Value, rightVal.Value.Value)),
                    ">" => new RuleValue(RuleValueType.Boolean, Compare(leftVal.Value, rightVal.Value) > 0),
                    "<" => new RuleValue(RuleValueType.Boolean, Compare(leftVal.Value, rightVal.Value) < 0),
                    ">=" => new RuleValue(RuleValueType.Boolean, Compare(leftVal.Value, rightVal.Value) >= 0),
                    "<=" => new RuleValue(RuleValueType.Boolean, Compare(leftVal.Value, rightVal.Value) <= 0),
                    "+" => new RuleValue(leftVal.Value.Type, Add(leftVal.Value, rightVal.Value)),
                    "-" => new RuleValue(leftVal.Value.Type, Subtract(leftVal.Value, rightVal.Value)),
                    "*" => new RuleValue(leftVal.Value.Type, Multiply(leftVal.Value, rightVal.Value)),
                    "/" => DivOp(leftVal.Value, rightVal.Value),
                    _ => throw new EvaluatorException("RF4001", $"Unknown operator: {bin.Operator}")
                };
                return new EvalResult(res, BuildTrace(expr, res, bin.Operator, T(leftVal.Trace, rightVal.Trace)));
            }

            if (expr is AnyAllExpression aa)
            {
                var arrResult = EvaluateNodeInternal(aa.ArrayExpr);
                if (arrResult.Value.Type != RuleValueType.Array)
                    throw new EvaluatorException("RF4002", "Cannot iterate non-array");
                var list = (List<RuleValue>)arrResult.Value.Value!;

                var childTraces = new List<TraceNode>();
                if (_traceEnabled && arrResult.Trace != null) childTraces.Add(arrResult.Trace);

                bool finalResult = aa.IsAll;

                for (int idx = 0; idx < list.Count; idx++)
                {
                    var item = list[idx];
                    _context["it"] = item.Value;
                    var itemResult = EvaluateNodeInternal(aa.WhereExpr);
                    if (itemResult.Trace != null) childTraces.Add(itemResult.Trace);

                    if (aa.IsAll)
                    {
                        if (!GetBool(itemResult.Value))
                        {
                            finalResult = false;
                            for (int j = idx + 1; j < list.Count; j++)
                            {
                                var phantom = BuildPhantom(aa.WhereExpr);
                                if (phantom != null) childTraces.Add(phantom);
                            }
                            break;
                        }
                    }
                    else
                    {
                        if (GetBool(itemResult.Value))
                        {
                            finalResult = true;
                            for (int j = idx + 1; j < list.Count; j++)
                            {
                                var phantom = BuildPhantom(aa.WhereExpr);
                                if (phantom != null) childTraces.Add(phantom);
                            }
                            break;
                        }
                    }
                }

                var value = new RuleValue(RuleValueType.Boolean, finalResult);
                string op = aa.IsAll ? "ALL" : "ANY";
                return new EvalResult(value, BuildTrace(expr, value, op, _traceEnabled ? childTraces : null));
            }

            if (expr is FilterMapExpression fm)
            {
                var arrResult = EvaluateNodeInternal(fm.ArrayExpr);
                if (arrResult.Value.Type != RuleValueType.Array)
                    throw new EvaluatorException("RF4002", "Cannot iterate non-array");
                var list = (List<RuleValue>)arrResult.Value.Value!;
                var result = new List<RuleValue>();

                var childTraces = new List<TraceNode>();
                if (_traceEnabled && arrResult.Trace != null) childTraces.Add(arrResult.Trace);

                foreach (var item in list)
                {
                    _context["it"] = item.Value;
                    var itemResult = EvaluateNodeInternal(fm.SubExpr);
                    if (itemResult.Trace != null) childTraces.Add(itemResult.Trace);

                    if (fm.IsMap)
                    {
                        result.Add(itemResult.Value);
                    }
                    else
                    {
                        if (itemResult.Value.Type == RuleValueType.Boolean && GetBool(itemResult.Value))
                            result.Add(item);
                    }
                }

                var value = new RuleValue(RuleValueType.Array, result);
                string op = fm.IsMap ? "MAP" : "FILTER";
                return new EvalResult(value, BuildTrace(expr, value, op, _traceEnabled ? childTraces : null));
            }

            if (expr is ArrayLiteralExpression arrLit)
            {
                var elements = new List<RuleValue>();
                var childTraces = new List<TraceNode>();
                foreach (var el in arrLit.Elements)
                {
                    var elResult = EvaluateNodeInternal(el);
                    elements.Add(elResult.Value);
                    if (elResult.Trace != null) childTraces.Add(elResult.Trace);
                }
                var value = new RuleValue(RuleValueType.Array, elements);
                return new EvalResult(value, BuildTrace(expr, value, null, _traceEnabled ? childTraces : null));
            }

            if (expr is ArrayIndexExpression arrIdx)
            {
                var arrResult = EvaluateNodeInternal(arrIdx.Array);
                var idxResult = EvaluateNodeInternal(arrIdx.Index);
                CheckNull(arrResult.Value, "ArrayIndex");
                if (arrResult.Value.Type != RuleValueType.Array)
                    throw new EvaluatorException("RF4002", "Cannot index non-array");
                if (idxResult.Value.Type != RuleValueType.Integer)
                    throw new EvaluatorException("RF4002", "Array index must be integer");

                var list = (List<RuleValue>)arrResult.Value.Value!;
                int index = (int)idxResult.Value.Value!;
                if (index < 0 || index >= list.Count)
                    throw new EvaluatorException("RF4002", $"Array index {index} out of bounds (0..{list.Count - 1})");

                var value = list[index];
                return new EvalResult(value, BuildTrace(expr, value, "[]", T(arrResult.Trace, idxResult.Trace)));
            }

            if (expr is FunctionCallExpression fc)
            {
                var args = new List<RuleValue>();
                var argTraces = new List<TraceNode>();
                foreach (var arg in fc.Arguments)
                {
                    var argResult = EvaluateNodeInternal(arg);
                    args.Add(argResult.Value);
                    if (argResult.Trace != null) argTraces.Add(argResult.Trace);
                }
                CheckNull(args[0], fc.Name);

                RuleValue res = fc.Name.ToUpperInvariant() switch
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
                return new EvalResult(res, BuildTrace(expr, res, fc.Name, _traceEnabled ? argTraces : null));
            }

            throw new EvaluatorException("RF4001", "Unknown AST node");
        }
        catch (EvaluatorException ex)
        {
            if (_traceEnabled && _errorTrace == null)
            {
                string? op = expr is BinaryExpression bin ? bin.Operator : null;
                _errorTrace = BuildTrace(expr, new RuleValue(RuleValueType.Null, null), op: op, error: ex);
            }
            throw;
        }
    }

    // === Existing helper methods (unchanged) ===

    private RuleValue DivOp(RuleValue l, RuleValue r)
    {
        if (Convert.ToDecimal(r.Value, CultureInfo.InvariantCulture) == 0)
            throw new EvaluatorException("RF4001", "Division by zero");
        return new RuleValue(RuleValueType.Decimal, Convert.ToDecimal(l.Value, CultureInfo.InvariantCulture) / Convert.ToDecimal(r.Value, CultureInfo.InvariantCulture));
    }

    public static object? UnwrapRuleValue(RuleValue val)
    {
        if (val.Type == RuleValueType.Array && val.Value is List<RuleValue> list)
        {
            return list.Select(UnwrapRuleValue).ToList();
        }
        return val.Value;
    }

    private void CheckNull(RuleValue val, string op)
    {
        if (val.Type == RuleValueType.Null)
            throw new EvaluatorException("RF4002", $"Cannot perform '{op}' on NULL. Use IS NULL / IS NOT NULL.");
    }

    private static bool GetBool(RuleValue val)
    {
        if (val.Value is bool b) return b;
        throw new EvaluatorException("RF4002", $"Expected Boolean, got {val.Type}");
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
        if (val is Dictionary<string, object?> dict) return new RuleValue(RuleValueType.Object, dict);
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
