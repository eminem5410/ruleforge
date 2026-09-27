using RuleForge.Core.Syntax;
using RuleForge.Core.Evaluation;
using System.Collections.Generic;

namespace RuleForge.Core.Compilation;

public class RuleForgeCompiler
{
private readonly List<RuleNode> _ast;

public RuleForgeCompiler(List<RuleNode> ast)
{
_ast = ast;
}

public List<Decision> Execute(Dictionary<string, object?> context)
{
// V9 Alpha delegates directly to the interpreter
var evaluator = new Evaluator(context);
return evaluator.EvaluateRules(_ast);
}
}
