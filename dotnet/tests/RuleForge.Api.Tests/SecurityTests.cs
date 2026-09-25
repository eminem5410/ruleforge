using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
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
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", "invalid_key");
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Fact]
    public async Task AUTH_003_ValidKeyAccepted()
    {
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", ValidKey);
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
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", AdminKey);
        var res = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        res.EnsureSuccessStatusCode();
    }

    [Fact]
    public async Task AUTH_006_RateLimitExceededAndRetryAfter()
    {
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", RateLimitKey1);
        
        // Send 100 requests (should be 200 OK)
        for (int i = 0; i < 100; i++)
        {
            var res = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
            Assert.True(res.IsSuccessStatusCode, $"Request {i+1} failed unexpectedly with {res.StatusCode}");
        }

        // Send 101st request (should be 429 Too Many Requests)
        var blockedRes = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        Assert.Equal(System.Net.HttpStatusCode.TooManyRequests, blockedRes.StatusCode);
        
        // Verify Retry-After header is present
        Assert.True(blockedRes.Headers.Contains("Retry-After"), "429 response must include Retry-After header");
    }

    [Fact]
    public async Task AUTH_007_IsolatedBuckets()
    {
        // 1. Exhaust the rate limit for RateLimitKey2
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", RateLimitKey2);
        for (int i = 0; i < 100; i++)
        {
            await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        }
        
        // 101st request for RateLimitKey2 should be 429
        var blockedRes = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        Assert.Equal(System.Net.HttpStatusCode.TooManyRequests, blockedRes.StatusCode);

        // 2. AdminKey should still have its full quota available
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", AdminKey);
        var adminRes = await _client.PostAsJsonAsync("/api/v1/evaluate", Request);
        Assert.True(adminRes.IsSuccessStatusCode, "AdminKey was blocked due to RateLimitKey2's rate limit!");
    }
}
