using System.Globalization;
using System;
using System.Collections.Generic;
using System.Linq;
using LinqExpr = System.Linq.Expressions.Expression;
using RuleForge.Core.Syntax;
using RuleForge.Core.Evaluation;
using RuleForge.Core.Lexing;

namespace RuleForge.Core.Compilation;

public class RuleForgeCompiler
{
    private readonly List<RuleNode> _ast;
    private readonly List<Func<Dictionary<string, object?>, bool>> _compiledRules = new();
    private readonly List<bool> _isCompiled = new();

    public RuleForgeCompiler(List<RuleNode> ast)
    {
        _ast = ast;
        foreach (var rule in ast)
        {
            try
            {
                var param = LinqExpr.Parameter(typeof(Dictionary<string, object?>), "ctx");
                var body = CompileNode(rule.WhenExpr, param);
                if (body.Type != typeof(bool)) throw new NotImplementedException();
                var lambda = LinqExpr.Lambda<Func<Dictionary<string, object?>, bool>>(body, param);
                _compiledRules.Add(lambda.Compile());
                _isCompiled.Add(true);
            }
            catch (NotImplementedException)
            {
                _compiledRules.Add(null!);
                _isCompiled.Add(false);
            }
        }
    }

    private LinqExpr CompileNode(Expression node, System.Linq.Expressions.ParameterExpression param)
    {
        if (node is LiteralExpression lit)
        {
            if (lit.Type == TokenType.BOOLEAN)
                return LinqExpr.Constant(lit.Value?.ToString() == "true", typeof(bool));
            if (lit.Type == TokenType.INTEGER)
                return LinqExpr.Constant(int.Parse(lit.Value!.ToString()!), typeof(int));
            if (lit.Type == TokenType.DECIMAL)
                return LinqExpr.Constant(decimal.Parse(lit.Value!.ToString()!, CultureInfo.InvariantCulture), typeof(decimal));
            if (lit.Type == TokenType.STRING)
                return LinqExpr.Constant(lit.Value?.ToString(), typeof(string));
            throw new NotImplementedException();
        }
        if (node is DateLiteralExpression dlit)
        {
            return LinqExpr.Constant(dlit.Value, typeof(DateOnly));
        }
        if (node is PropertyExpression prop)
        {
            var call = LinqExpr.Call(typeof(RuleForgeCompiler), "GetProperty", null, param, LinqExpr.Constant(prop.ObjectName), LinqExpr.Constant(prop.PropertyName));
            return call;
        }
        if (node is FunctionCallExpression fc)
        {
            if (fc.Name.ToUpper() == "LENGTH" && fc.Arguments.Count == 1)
            {
                var arg = CompileNode(fc.Arguments[0], param);
                if (arg.Type == typeof(object)) arg = LinqExpr.Convert(arg, typeof(string));
                if (arg.Type != typeof(string)) throw new NotImplementedException();
                return LinqExpr.Property(arg, "Length");
            }
            if (fc.Name.ToUpper() == "CONTAINS" && fc.Arguments.Count == 2)
            {
                var arg1 = CompileNode(fc.Arguments[0], param);
                var arg2 = CompileNode(fc.Arguments[1], param);
                if (arg1.Type == typeof(object)) arg1 = LinqExpr.Convert(arg1, typeof(string));
                if (arg2.Type == typeof(object)) arg2 = LinqExpr.Convert(arg2, typeof(string));
                if (arg1.Type != typeof(string) || arg2.Type != typeof(string)) throw new NotImplementedException();
                
                var method = typeof(string).GetMethod("Contains", new[] { typeof(string) });
                return LinqExpr.Call(arg1, method!, arg2);
            }
            if (fc.Name.ToUpper() == "DATE_ADD" && fc.Arguments.Count == 2)
            {
                var d = CompileNode(fc.Arguments[0], param);
                if (d.Type == typeof(object)) d = LinqExpr.Call(typeof(RuleForgeCompiler), "GetDate", null, d);
                if (d.Type != typeof(DateOnly)) throw new NotImplementedException();
                
                var days = CompileNode(fc.Arguments[1], param);
                if (days.Type == typeof(object)) days = LinqExpr.Convert(days, typeof(int));
                if (days.Type != typeof(int)) throw new NotImplementedException();
                
                var addDaysMethod = typeof(DateOnly).GetMethod("AddDays", new[] { typeof(int) });
                return LinqExpr.Call(d, addDaysMethod!, days);
            }
            if (fc.Name.ToUpper() == "DATE_DIFF" && fc.Arguments.Count == 2)
            {
                var d1 = CompileNode(fc.Arguments[0], param);
                var d2 = CompileNode(fc.Arguments[1], param);
                if (d1.Type == typeof(object)) d1 = LinqExpr.Call(typeof(RuleForgeCompiler), "GetDate", null, d1);
                if (d2.Type == typeof(object)) d2 = LinqExpr.Call(typeof(RuleForgeCompiler), "GetDate", null, d2);
                if (d1.Type != typeof(DateOnly) || d2.Type != typeof(DateOnly)) throw new NotImplementedException();
                
                return LinqExpr.Subtract(LinqExpr.Property(d2, "DayNumber"), LinqExpr.Property(d1, "DayNumber"));
            }
            if (fc.Name.ToUpper() == "EXTRACT" && fc.Arguments.Count == 2)
            {
                if (!(fc.Arguments[1] is LiteralExpression lit2) || lit2.Type != TokenType.STRING) throw new NotImplementedException();
                var d = CompileNode(fc.Arguments[0], param);
                if (d.Type == typeof(object)) d = LinqExpr.Call(typeof(RuleForgeCompiler), "GetDate", null, d);
                if (d.Type != typeof(DateOnly)) throw new NotImplementedException();
                
                return lit2.Value?.ToString() switch
                {
                    "year" => LinqExpr.Property(d, "Year"),
                    "month" => LinqExpr.Property(d, "Month"),
                    "day" => LinqExpr.Property(d, "Day"),
                    _ => throw new NotImplementedException()
                };
            }
            throw new NotImplementedException();
        }
        if (node is ArrayLiteralExpression arrLit)
        {
            var elements = arrLit.Elements.Select(e => {
                var comp = CompileNode(e, param);
                if (comp.Type == typeof(int)) comp = LinqExpr.Convert(comp, typeof(object));
                else if (comp.Type == typeof(string)) comp = LinqExpr.Convert(comp, typeof(object));
                else if (comp.Type == typeof(bool)) comp = LinqExpr.Convert(comp, typeof(object));
                else if (comp.Type == typeof(decimal)) comp = LinqExpr.Convert(comp, typeof(object));
                return comp;
            }).ToArray();
            return LinqExpr.Call(typeof(RuleForgeCompiler), "CreateArray", null, elements);
        }
        if (node is ArrayIndexExpression arrIdx)
        {
            var arr = CompileNode(arrIdx.Array, param);
            if (arr.Type != typeof(object)) arr = LinqExpr.Convert(arr, typeof(object));
            
            var idx = CompileNode(arrIdx.Index, param);
            if (idx.Type == typeof(object)) idx = LinqExpr.Convert(idx, typeof(int));
            if (idx.Type != typeof(int)) throw new NotImplementedException();
            
            return LinqExpr.Call(typeof(RuleForgeCompiler), "SafeIndex", null, arr, idx);
        }
        if (node is NullCheckExpression nc)
        {
            var left = CompileNode(nc.Left, param);
            // Box value types (like int) to object before comparing to null
            if (left.Type.IsValueType) left = LinqExpr.Convert(left, typeof(object));
            var nullConst = LinqExpr.Constant(null, typeof(object));
            return nc.IsNot ? LinqExpr.NotEqual(left, nullConst) : LinqExpr.Equal(left, nullConst);
        }
        if (node is BinaryExpression bin)
        {
            if (bin.Operator == "AND") return LinqExpr.AndAlso(EnsureBool(CompileNode(bin.Left, param)), EnsureBool(CompileNode(bin.Right, param)));
            if (bin.Operator == "OR") return LinqExpr.OrElse(EnsureBool(CompileNode(bin.Left, param)), EnsureBool(CompileNode(bin.Right, param)));
            
            if (bin.Operator == "+" || bin.Operator == "-" || bin.Operator == "*" || bin.Operator == "/")
            {
                var left = CompileNode(bin.Left, param);
                var right = CompileNode(bin.Right, param);
                
                if (left.Type == typeof(object) && right.Type != typeof(object))
                    left = LinqExpr.Convert(left, right.Type);
                else if (right.Type == typeof(object) && left.Type != typeof(object))
                    right = LinqExpr.Convert(right, left.Type);
                else if (left.Type == typeof(object) && right.Type == typeof(object))
                    throw new NotImplementedException();

                // Promote int to decimal if one side is decimal
                if (left.Type == typeof(int) && right.Type == typeof(decimal))
                    left = LinqExpr.Convert(left, typeof(decimal));
                else if (right.Type == typeof(int) && left.Type == typeof(decimal))
                    right = LinqExpr.Convert(right, typeof(decimal));

                if (left.Type == typeof(string) && right.Type == typeof(string))
                {
                    var concatMethod = typeof(string).GetMethod("Concat", new[] { typeof(string), typeof(string) });
                    return LinqExpr.Add(left, right, concatMethod);
                }

                return bin.Operator switch
                {
                    "+" => LinqExpr.Add(left, right),
                    "-" => LinqExpr.Subtract(left, right),
                    "*" => LinqExpr.Multiply(left, right),
                    "/" => LinqExpr.Divide(left, right),
                    _ => throw new NotImplementedException()
                };
            }
            if (bin.Operator == "==" || bin.Operator == "!=" || bin.Operator == ">" || bin.Operator == "<" || bin.Operator == ">=" || bin.Operator == "<=")
            {
                var left = CompileNode(bin.Left, param);
                var right = CompileNode(bin.Right, param);
                
                if (left.Type == typeof(object) && right.Type != typeof(object))
                    left = LinqExpr.Convert(left, right.Type);
                else if (right.Type == typeof(object) && left.Type != typeof(object))
                    right = LinqExpr.Convert(right, left.Type);
                else if (left.Type == typeof(object) && right.Type == typeof(object))
                    throw new NotImplementedException();

                return bin.Operator switch
                {
                    "==" => LinqExpr.Equal(left, right),
                    "!=" => LinqExpr.NotEqual(left, right),
                    ">" => LinqExpr.GreaterThan(left, right),
                    "<" => LinqExpr.LessThan(left, right),
                    ">=" => LinqExpr.GreaterThanOrEqual(left, right),
                    "<=" => LinqExpr.LessThanOrEqual(left, right),
                    _ => throw new NotImplementedException()
                };
            }
            throw new NotImplementedException();
        }
        if (node is UnaryExpression un)
        {
            if (un.Operator == "NOT") return LinqExpr.Not(EnsureBool(CompileNode(un.Operand, param)));
            throw new NotImplementedException();
        }
        throw new NotImplementedException();
    }

    private LinqExpr EnsureBool(LinqExpr expr)
    {
        if (expr.Type == typeof(bool)) return expr;
        if (expr.Type == typeof(object)) return LinqExpr.Convert(expr, typeof(bool));
        throw new NotImplementedException();
    }

    public static DateOnly GetDate(object? val)
    {
        if (val is DateOnly d) return d;
        if (val is string s && DateOnly.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var parsed)) return parsed;
        throw new NotImplementedException();
    }

    public static List<object?> CreateArray(params object?[] items) => items.ToList();
    
    public static object? SafeIndex(object? arr, int idx)
    {
        if (arr == null || arr is not List<object?> list) throw new NotImplementedException();
        if (idx < 0 || idx >= list.Count) throw new NotImplementedException();
        return list[idx];
    }

    public static object? GetProperty(Dictionary<string, object?> ctx, string objName, string propName)
    {
        if (ctx.TryGetValue(objName, out var val) && val is Dictionary<string, object?> dict)
        {
            return dict.TryGetValue(propName, out var propVal) ? propVal : null;
        }
        return null;
    }

    public List<Decision> Execute(Dictionary<string, object?> context)
    {
        var evaluator = new Evaluator(context);
        var decisions = new List<Decision>();
        for (int i = 0; i < _ast.Count; i++)
        {
            var rule = _ast[i];
            if (_isCompiled[i])
            {
                bool conditionResult = false;
                try
                {
                    conditionResult = _compiledRules[i](context);
                }
                catch (Exception)
                {
                    // Fallback to interpreter on runtime error
                    decisions.Add(evaluator.EvaluateRules(new List<RuleNode> { rule })[0]);
                    continue;
                }
                
                // Slice 2: Resolve actions directly without Evaluator
                var rawActions = conditionResult ? rule.ThenActions : (rule.ElseActions.Count > 0 ? rule.ElseActions : new List<ActionNode> { new ActionNode("NO_ACTION") });
                var resolvedActions = new List<ActionNode>();
                
                foreach (var a in rawActions)
                {
                    if (a is EmitActionNode emit)
                    {
                        object? payload = null;
                        if (emit.PayloadPath != null)
                        {
                            var payloadVal = evaluator.EvaluateNode(emit.PayloadPath);
                            payload = Evaluator.UnwrapRuleValue(payloadVal);
                        }
                        resolvedActions.Add(new ActionNode("EMIT", emit.IntentName, payload));
                    }
                    else
                    {
                        resolvedActions.Add(a);
                    }
                }
                decisions.Add(evaluator.BuildDecision(rule, conditionResult, resolvedActions));
            }
            else
            {
                decisions.Add(evaluator.EvaluateRules(new List<RuleNode> { rule })[0]);
            }
        }
        return decisions;
    }
}
