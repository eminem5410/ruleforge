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
            throw new NotImplementedException();
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
