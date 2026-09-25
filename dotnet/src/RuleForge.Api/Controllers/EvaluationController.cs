using RuleForge.Api.Services;
using Microsoft.AspNetCore.Mvc;
using RuleForge.Api.Contracts;
using RuleForge.Core.Evaluation;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using System.Text.Json;

namespace RuleForge.Api.Controllers;

[ApiController]
[Route("api/v1")]
public class EvaluationController : ControllerBase
{
    [HttpPost("evaluate")]
    public IActionResult Evaluate([FromBody] EvaluateRequest request)
    {
        // 1. Normalize Context (JSON to .NET types)
        var context = ContextNormalizer.Normalize(request.Context, request.ContextSchema);
        
        // 2. Execute Pipeline
        var tokens = new Lexer(request.Source).Tokenize();
        var ast = new Parser(tokens).Parse();
        new SemanticAnalyzer(request.ContextSchema).Analyze(ast);
        var decisions = new Evaluator(context).EvaluateRules(ast);

        // 3. Map to DTO
        var response = new EvaluateResponse
        {
            Decisions = decisions.Select(d => new DecisionDto
            {
                RuleId = d.RuleId,
                Matched = d.Matched,
                Actions = d.Actions.Select(a => new ActionDto { Type = a.ActionType, Value = a.Value }).ToList()
            }).ToList()
        };

        return Ok(response);
    }
}
