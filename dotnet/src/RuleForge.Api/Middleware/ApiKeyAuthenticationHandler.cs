using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;

namespace RuleForge.Api.Middleware;

public class ApiKeyAuthenticationHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    // Mapeo explícito de Secreto -> (ID, Scopes)
    private static readonly Dictionary<string, (string Id, string[] Scopes)> ApiKeys = new()
    {
        { "rf_live_test_key_123", ("test-key", new[] { "rules:evaluate", "rules:read" }) },
        { "rf_live_admin_key_456", ("admin-key", new[] { "rules:evaluate", "rules:read", "rules:write", "rules:admin" }) },
        { "rf_live_rl_key_1", ("rl-key-1", new[] { "rules:evaluate", "rules:read" }) },
        { "rf_live_rl_key_2", ("rl-key-2", new[] { "rules:evaluate", "rules:read" }) },
        { "rf_live_no_scope_key", ("no-scope-key", Array.Empty<string>()) }
    };

    public ApiKeyAuthenticationHandler(IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger, UrlEncoder encoder) 
        : base(options, logger, encoder) { }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        if (!Request.Headers.TryGetValue("Authorization", out var authHeader))
            return Task.FromResult(AuthenticateResult.Fail("Missing Authorization header"));

        var headerValue = authHeader.ToString();
        if (!headerValue.StartsWith("ApiKey ", StringComparison.OrdinalIgnoreCase))
            return Task.FromResult(AuthenticateResult.Fail("Invalid scheme. Expected 'ApiKey'."));

        var token = headerValue.Substring("ApiKey ".Length).Trim();

        if (!ApiKeys.TryGetValue(token, out var keyInfo))
            return Task.FromResult(AuthenticateResult.Fail("Invalid API Key"));

        var claims = keyInfo.Scopes.Select(s => new Claim("scope", s)).ToList();
        // Usar el ID sanitizado para el Rate Limiter y logs
        claims.Add(new Claim("api_key_id", keyInfo.Id));
        
        var identity = new ClaimsIdentity(claims, Scheme.Name);
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, Scheme.Name);

        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}
