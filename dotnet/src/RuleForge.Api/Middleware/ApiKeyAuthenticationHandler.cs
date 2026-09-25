using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;

namespace RuleForge.Api.Middleware;

public class ApiKeyAuthenticationHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    private static readonly Dictionary<string, string[]> ApiKeys = new()
    {
        { "rf_live_test_key_123", new[] { "rules:evaluate", "rules:read" } },
        { "rf_live_admin_key_456", new[] { "rules:evaluate", "rules:read", "rules:write", "rules:admin" } },
        { "rf_live_rl_key_1", new[] { "rules:evaluate", "rules:read" } },
        { "rf_live_rl_key_2", new[] { "rules:evaluate", "rules:read" } }
    };

    public ApiKeyAuthenticationHandler(IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger, UrlEncoder encoder) 
        : base(options, logger, encoder) { }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        if (!Request.Headers.TryGetValue("Authorization", out var authHeader))
            return Task.FromResult(AuthenticateResult.Fail("Missing Authorization header"));

        var headerValue = authHeader.ToString();
        if (!headerValue.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
            return Task.FromResult(AuthenticateResult.Fail("Invalid scheme. Expected 'Bearer'."));

        var token = headerValue.Substring("Bearer ".Length).Trim();

        if (!ApiKeys.TryGetValue(token, out var scopes))
            return Task.FromResult(AuthenticateResult.Fail("Invalid API Key"));

        var claims = scopes.Select(s => new Claim("scope", s)).ToList();
        // Fix: Use full token as api_key_id to ensure unique rate limit buckets
        claims.Add(new Claim("api_key_id", token));
        
        var identity = new ClaimsIdentity(claims, Scheme.Name);
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, Scheme.Name);

        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}
