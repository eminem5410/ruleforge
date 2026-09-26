using System.IdentityModel.Tokens.Jwt;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.IdentityModel.Tokens;
using Xunit;

namespace RuleForge.Api.Tests;

public class JwtSecurityTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;
    private const string SigningKey = "SuperSecretDevKeyNeedsToBeLongEnoughForHmacSha256";
    private const string Issuer = "ruleforge";
    private const string Audience = "ruleforge-api";

    public JwtSecurityTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.CreateClient();
    }

    private static readonly object RequestPayload = new
    {
        source = "RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END",
        context_schema = new { customer = new { age = "Integer" } },
        context = new { customer = new { age = 21 } }
    };

    private string GenerateJwt(DateTime? expires = null, string? issuer = null, string? audience = null, string? signingKey = null, string scopes = "rules:evaluate", string sub = "test-user-123")
    {
        var claims = new List<Claim>
        {
            new("sub", sub),
            new("scope", scopes)
        };

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(signingKey ?? SigningKey));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var token = new JwtSecurityToken(
            issuer: issuer ?? Issuer,
            audience: audience ?? Audience,
            claims: claims,
            expires: expires ?? DateTime.UtcNow.AddMinutes(10),
            signingCredentials: creds
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    [Fact]
    public async Task JWT_001_ValidTokenAccepted()
    {
        var token = GenerateJwt();
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", RequestPayload);
        res.EnsureSuccessStatusCode();
    }

    [Fact]
    public async Task JWT_002_ExpiredTokenRejected()
    {
        var token = GenerateJwt(expires: DateTime.UtcNow.AddMinutes(-5));
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", RequestPayload);
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Fact]
    public async Task JWT_003_InvalidIssuerRejected()
    {
        var token = GenerateJwt(issuer: "wrong-issuer");
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", RequestPayload);
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Fact]
    public async Task JWT_004_InvalidAudienceRejected()
    {
        var token = GenerateJwt(audience: "wrong-audience");
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", RequestPayload);
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Fact]
    public async Task JWT_005_MissingScopeForbidden()
    {
        var token = GenerateJwt(scopes: "rules:read");
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", RequestPayload);
        Assert.Equal(System.Net.HttpStatusCode.Forbidden, res.StatusCode);
    }

    [Fact]
    public async Task JWT_006_InvalidSignatureRejected()
    {
        var token = GenerateJwt(signingKey: "WrongKeyThatIsAlsoLongEnoughForHmacSha256AlgorithmToWork");
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", RequestPayload);
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Fact]
    public async Task JWT_007_SharedBucketsBySub()
    {
        var token1 = GenerateJwt(sub: "rl-shared-jwt-user");
        var token2 = GenerateJwt(sub: "rl-shared-jwt-user"); // Same sub, different token instance
        
        // Exhaust limit with token1
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token1);
        for (int i = 0; i < 100; i++)
        {
            var res = await _client.PostAsJsonAsync("/api/v1/evaluate", RequestPayload);
            Assert.True(res.IsSuccessStatusCode);
        }

        // Token1 should be blocked now
        var blockedRes1 = await _client.PostAsJsonAsync("/api/v1/evaluate", RequestPayload);
        Assert.Equal(System.Net.HttpStatusCode.TooManyRequests, blockedRes1.StatusCode);

        // Token2 (same sub) should ALSO be blocked because it shares the bucket
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token2);
        var blockedRes2 = await _client.PostAsJsonAsync("/api/v1/evaluate", RequestPayload);
        Assert.Equal(System.Net.HttpStatusCode.TooManyRequests, blockedRes2.StatusCode);
    }
}
