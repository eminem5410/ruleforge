using RuleForge.Core.Syntax;
using RuleForge.Core.Lexing;
using System.Linq;

namespace RuleForge.Core.Semantic;

public class SemanticAnalyzer
{
    private readonly Dictionary<string, Dictionary<string, string>> _schema;
    private string? _itType = null;

    public SemanticAnalyzer(Dictionary<string, Dictionary<string, string>> schema)
    {
        _schema = schema;
    }

    public void Analyze(List<RuleNode> ast)
    {
        foreach (var rule in ast)
        {
            AnalyzeRule(rule);
        }
    }

    private void AnalyzeRule(RuleNode rule)
    {
        foreach (var action in rule.ThenActions.Concat(rule.ElseActions))
        {
            if (action is SetActionNode setAction)
            {
                var parts = setAction.Path.Split('.');
                if (parts.Length != 2 || !_schema.ContainsKey(parts[0]))
                    throw new SemanticException("RF3002", $"Context object '{parts[0]}' not defined");
                if (!_schema[parts[0]].TryGetValue(parts[1], out var propType))
                    throw new SemanticException("RF3002", $"Property '{parts[1]}' not found in '{parts[0]}'");
                var valType = CheckNode(setAction.ValueExpr);
                if (valType != propType) throw new SemanticException("RF3001", $"Cannot assign {valType} to {propType}");
            }
            if (action is EmitActionNode emitAction && emitAction.PayloadPath != null)
            {
                if (emitAction.PayloadPath is PropertyExpression propExpr && !_schema.ContainsKey(propExpr.ObjectName))
                {
                    throw new SemanticException("RF3002", $"Context object '{propExpr.ObjectName}' not defined");
                }
                else if (emitAction.PayloadPath is not PropertyExpression)
                {
                    CheckNode(emitAction.PayloadPath);
                }
            }
        }

        CheckActions(rule.ThenActions);
        CheckActions(rule.ElseActions);
        
        int depth = 0, count = 0;
        CheckAstLimits(rule.WhenExpr, 1, ref depth, ref count);
        if (depth > 50) throw new SemanticException("RF5001", $"Security Limit: AST depth exceeds maximum of 50");
        if (count > 500) throw new SemanticException("RF5002", $"Security Limit: AST node count exceeds maximum of 500");

        var exprType = CheckNode(rule.WhenExpr);
        if (exprType != "Boolean")
            throw new SemanticException("RF3002", $"WHEN condition must evaluate to Boolean, got {exprType}");
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
        else if (expr is FunctionCallExpression fc)
        {
            foreach (var arg in fc.Arguments) CheckAstLimits(arg, currentDepth + 1, ref maxDepth, ref count);
        }
        else if (expr is ArrayLiteralExpression arrLit)
        {
            foreach (var el in arrLit.Elements) CheckAstLimits(el, currentDepth + 1, ref maxDepth, ref count);
        }
        else if (expr is ArrayIndexExpression arrIdx)
        {
            CheckAstLimits(arrIdx.Array, currentDepth + 1, ref maxDepth, ref count);
            CheckAstLimits(arrIdx.Index, currentDepth + 1, ref maxDepth, ref count);
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
        if (expr is DateLiteralExpression dlit)
        {
            return "Date";
        }
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
                if (validNumerics.Contains(l) && validNumerics.Contains(r)) return "Boolean";
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
                if (op == "+" && l == "String" && r == "String")
                    return "String";
                if (!validNumerics.Contains(l) || !validNumerics.Contains(r))
                    throw new SemanticException("RF3001", $"Operator '{op}' requires numeric or String operands");
                return "Decimal";
            }
        }
        if (expr is ItExpression)
        {
            return _itType ?? "Unknown";
        }
        if (expr is AnyAllExpression aa)
        {
            var arrType = CheckNode(aa.ArrayExpr);
            if (!arrType.StartsWith("Array<")) throw new SemanticException("RF3003", "ANY/ALL requires an array");
            var innerType = arrType.Substring(6, arrType.Length - 7);
            
            _itType = innerType;
            var whereType = CheckNode(aa.WhereExpr);
            _itType = null;
            
            if (whereType != "Boolean") throw new SemanticException("RF3003", "WHERE clause must be Boolean");
            return "Boolean";
        }
        if (expr is ArrayLiteralExpression arrLit)
        {
            if (!arrLit.Elements.Any()) return "Array<Null>";
            
            var firstType = CheckNode(arrLit.Elements[0]);
            foreach (var el in arrLit.Elements.Skip(1))
            {
                if (CheckNode(el) != firstType)
                    throw new SemanticException("RF3003", "Heterogeneous array literal");
            }
            return $"Array<{firstType}>";
        }
        if (expr is ArrayIndexExpression arrIdx)
        {
            var arrType = CheckNode(arrIdx.Array);
            var idxType = CheckNode(arrIdx.Index);
            
            if (idxType != "Integer")
                throw new SemanticException("RF3003", "Array index must be Integer");
                
            if (!arrType.StartsWith("Array<"))
                throw new SemanticException("RF3003", $"Cannot index non-array type {arrType}");
                
            return arrType.Substring(6, arrType.Length - 7);
        }
        if (expr is FunctionCallExpression fc)
        {
            if (fc.Name.ToUpper() == "DATE_ADD")
            {
                if (fc.Arguments.Count != 2) throw new SemanticException("RF3003", "Function 'DATE_ADD' expects 2 arguments");
                var arg1 = CheckNode(fc.Arguments[0]);
                var arg2 = CheckNode(fc.Arguments[1]);
                if (arg1 != "Date") throw new SemanticException("RF3003", $"Argument 1 of 'DATE_ADD' must be Date, got {arg1}");
                if (arg2 != "Integer") throw new SemanticException("RF3003", $"Argument 2 of 'DATE_ADD' must be Integer, got {arg2}");
                return "Date";
            }
            if (fc.Name.ToUpper() == "DATE_DIFF")
            {
                if (fc.Arguments.Count != 2) throw new SemanticException("RF3003", "Function 'DATE_DIFF' expects 2 arguments");
                var arg1 = CheckNode(fc.Arguments[0]);
                var arg2 = CheckNode(fc.Arguments[1]);
                if (arg1 != "Date" || arg2 != "Date") throw new SemanticException("RF3003", "Function 'DATE_DIFF' requires Date arguments");
                return "Integer";
            }
            if (fc.Name.ToUpper() == "EXTRACT")
            {
                if (fc.Arguments.Count != 2) throw new SemanticException("RF3003", "Function 'EXTRACT' expects 2 arguments");
                var arg1 = CheckNode(fc.Arguments[0]);
                if (arg1 != "Date") throw new SemanticException("RF3003", $"Argument 1 of 'EXTRACT' must be Date, got {arg1}");
                if (!(fc.Arguments[1] is LiteralExpression strLit) || strLit.Type != TokenType.STRING) throw new SemanticException("RF3003", "Argument 2 of 'EXTRACT' must be String literal");
                var part = strLit.Value?.ToString();
                if (part != "year" && part != "month" && part != "day") throw new SemanticException("RF3003", "Invalid part for EXTRACT. Expected 'year', 'month', or 'day'");
                return "Integer";
            }
            if (fc.Name.ToLower() == "length")
            {
                if (fc.Arguments.Count != 1) throw new SemanticException("RF3003", "Function 'length' expects 1 argument");
                var argType = CheckNode(fc.Arguments[0]);
                if (argType != "String" && !argType.StartsWith("Array<"))
                    throw new SemanticException("RF3003", $"Function 'length' expects a String or Array, got {argType}");
                return "Integer";
            }
            if (fc.Name.ToLower() == "contains")
            {
                if (fc.Arguments.Count != 2) throw new SemanticException("RF3003", "Function 'contains' expects 2 arguments");
                var arg1Type = CheckNode(fc.Arguments[0]);
                var arg2Type = CheckNode(fc.Arguments[1]);
                
                if (arg1Type == "String")
                {
                    if (arg2Type != "String") throw new SemanticException("RF3003", "CONTAINS expects String, got " + arg2Type);
                }
                else if (arg1Type.StartsWith("Array<"))
                {
                    var innerType = arg1Type.Substring(6, arg1Type.Length - 7);
                    if (innerType == "Null") throw new SemanticException("RF3003", "Cannot infer array type from empty array literal in 'contains'");
                    if (innerType != arg2Type) throw new SemanticException("RF3003", $"Argument 2 of 'contains' must be {innerType}, got {arg2Type}");
                }
                else
                {
                    throw new SemanticException("RF3003", $"Function 'contains' expects a String or Array as first argument, got {arg1Type}");
                }
                return "Boolean";
            }
            if (fc.Name.ToLower() == "starts_with" || fc.Name.ToLower() == "ends_with")
            {
                if (fc.Arguments.Count != 2) throw new SemanticException("RF3003", $"Function '{fc.Name}' expects 2 arguments");
                if (CheckNode(fc.Arguments[0]) != "String" || CheckNode(fc.Arguments[1]) != "String")
                    throw new SemanticException("RF3003", $"Function '{fc.Name}' requires String arguments");
                return "Boolean";
            }
            if (fc.Name.ToLower() == "abs")
            {
                if (fc.Arguments.Count != 1) throw new SemanticException("RF3003", "Function 'abs' expects 1 argument");
                var t = CheckNode(fc.Arguments[0]);
                if (t != "Integer" && t != "Decimal") throw new SemanticException("RF3003", "Function 'abs' requires Numeric argument");
                return t;
            }
            throw new SemanticException("RF3003", $"Unknown function '{fc.Name}'");
        }
        throw new SemanticException("RF3003", "Unknown AST node");
    }
}
