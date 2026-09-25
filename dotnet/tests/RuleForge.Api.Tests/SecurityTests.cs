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
        
        var content = await res.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(content);
        Assert.True(doc.RootElement.GetProperty("decisions")[0].GetProperty("matched").GetBoolean());
    }

    [Fact]
    public async Task AUTH_004_HealthEndpointNoAuthRequired()
    {
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
}
