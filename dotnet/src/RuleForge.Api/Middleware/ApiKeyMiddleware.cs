using System.Security.Claims;
using System.Text;

namespace RuleForge.Api.Middleware;

public class ApiKeyMiddleware
{
    private readonly RequestDelegate _next;
    private const string ApiKeyHeader = "Authorization";

    // In-memory store for demo. In production, this would be a database.
    private static readonly Dictionary<string, string[]> ApiKeys = new()
    {
        { "rf_live_test_key_123", new[] { "rules:evaluate", "rules:read" } },
        { "rf_live_admin_key_456", new[] { "rules:evaluate", "rules:read", "rules:write", "rules:admin" } }
    };

    public ApiKeyMiddleware(RequestDelegate next)
    {
        _next = next;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        // Skip auth for Swagger and health endpoints
        var path = context.Request.Path.Value ?? "";
        if (path.StartsWith("/swagger") || path.StartsWith("/health"))
        {
            await _next(context);
            return;
        }

        if (!context.Request.Headers.TryGetValue(ApiKeyHeader, out var authHeader))
        {
            context.Response.StatusCode = 401;
            await context.Response.WriteAsync("{\"status\":\"error\",\"error_code\":\"UNAUTHORIZED\"}");
            return;
        }

        var headerValue = authHeader.ToString();
        if (!headerValue.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            context.Response.StatusCode = 401;
            await context.Response.WriteAsync("{\"status\":\"error\",\"error_code\":\"UNAUTHORIZED\"}");
            return;
        }

        var token = headerValue.Substring("Bearer ".Length).Trim();

        if (!ApiKeys.TryGetValue(token, out var scopes))
        {
            context.Response.StatusCode = 401;
            await context.Response.WriteAsync("{\"status\":\"error\",\"error_code\":\"INVALID_API_KEY\"}");
            return;
        }

        // Create claims with scopes
        var claims = scopes.Select(s => new Claim("scope", s)).ToList();
        claims.Add(new Claim("api_key", token));
        
        var identity = new ClaimsIdentity(claims, "ApiKey");
        context.User = new ClaimsPrincipal(identity);

        await _next(context);
    }
}
