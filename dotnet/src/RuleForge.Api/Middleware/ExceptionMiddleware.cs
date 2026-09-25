using System.Text.Json;
using RuleForge.Api.Contracts;
using RuleForge.Core.Evaluation;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;

namespace RuleForge.Api.Middleware;

public class ExceptionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ExceptionMiddleware> _logger;

    public ExceptionMiddleware(RequestDelegate next, ILogger<ExceptionMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task Invoke(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            // Log the real exception so we can see it in tests/logs
            _logger.LogError(ex, "Unhandled exception in RuleForge API");
            
            context.Response.StatusCode = 400;
            context.Response.ContentType = "application/json";
            
            string errorCode = ex switch
            {
                LexerException => "RF1xxx",
                ParserException => "RF2xxx",
                SemanticException => "RF3xxx",
                EvaluatorException => "RF4xxx",
                _ => "INTERNAL"
            };

            var response = new ErrorResponse { ErrorCode = errorCode };
            await context.Response.WriteAsync(JsonSerializer.Serialize(response));
        }
    }
}
