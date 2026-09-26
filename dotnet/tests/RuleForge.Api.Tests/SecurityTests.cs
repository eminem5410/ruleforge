using System.Net.Http.Headers;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace RuleForge.Api.Tests;

public class SecurityTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;
    private const string ValidKey = "rf_live_test_key_123";
    private const string AdminKey = "rf_live_admin_key_456";
    private const string RateLimitKey1 = "rf_live_rl_key_1";
    private const string RateLimitKey2 = "rf_live_rl_key_2";

    public SecurityTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.CreateClient();
    }

    private static readonly object Request = new
    {
        source = "RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END",
        context_schema = new { customer = new { age = "Integer" } },
        context = new { customer = new { age = 21 } }
    };

    [Fact]
    public async Task AUTH_001_UnauthenticatedRejected()
    {
        _client.DefaultRequestHeaders.Authorization = null;
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Fact]
    public async Task AUTH_002_InvalidKeyRejected()
    {
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("ApiKey", "invalid_key");
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Fact]
    public async Task AUTH_003_ValidKeyAccepted()
    {
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("ApiKey", ValidKey);
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        res.EnsureSuccessStatusCode();
    }

    [Fact]
    public async Task AUTH_004_HealthEndpointNoAuthRequired()
    {
        _client.DefaultRequestHeaders.Authorization = null;
        var res = await _client.GetAsync("/api/v1/health");
        res.EnsureSuccessStatusCode();
    }

    [Fact]
    public async Task AUTH_005_AdminKeyAlsoWorksForEvaluate()
    {
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("ApiKey", AdminKey);
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        res.EnsureSuccessStatusCode();
    }

    [Fact]
    public async Task AUTH_006_RateLimitExceededAndRetryAfter()
    {
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("ApiKey", RateLimitKey1);
        
        for (int i = 0; i < 100; i++)
        {
            var res = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
            Assert.True(res.IsSuccessStatusCode, $"Request {i+1} failed unexpectedly with {res.StatusCode}");
        }

        var blockedRes = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        Assert.Equal(System.Net.HttpStatusCode.TooManyRequests, blockedRes.StatusCode);
        Assert.True(blockedRes.Headers.Contains("Retry-After"), "429 response must include Retry-After header");
    }

    [Fact]
    public async Task AUTH_007_IsolatedBuckets()
    {
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("ApiKey", RateLimitKey2);
        for (int i = 0; i < 100; i++)
        {
            await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        }
        
        var blockedRes = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        Assert.Equal(System.Net.HttpStatusCode.TooManyRequests, blockedRes.StatusCode);

        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("ApiKey", AdminKey);
        var adminRes = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        Assert.True(adminRes.IsSuccessStatusCode, "AdminKey was blocked due to RateLimitKey2's rate limit!");
    }
}
