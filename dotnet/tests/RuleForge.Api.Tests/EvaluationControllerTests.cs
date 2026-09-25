using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace RuleForge.Api.Tests;

public class EvaluationControllerTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;

    public EvaluationControllerTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task API_001_EvaluateBasicRule()
    {
        var request = new
        {
            Source = "RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END",
            ContextSchema = new { customer = new { age = "Integer" } },
            Context = new { customer = new { age = 21 } }
        };

        var response = await _client.PostAsJsonAsync("/api/v1/evaluate", request);
        response.EnsureSuccessStatusCode();

        var content = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(content);
        
        Assert.Equal("ok", doc.RootElement.GetProperty("status").GetString());
        Assert.True(doc.RootElement.GetProperty("decisions")[0].GetProperty("matched").GetBoolean());
    }

    [Fact]
    public async Task API_002_EvaluateDeny()
    {
        var request = new
        {
            Source = "RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW ELSE DENY \"Too young\" END",
            ContextSchema = new { customer = new { age = "Integer" } },
            Context = new { customer = new { age = 16 } }
        };

        var response = await _client.PostAsJsonAsync("/api/v1/evaluate", request);
        response.EnsureSuccessStatusCode();
        
        var content = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(content);
        
        Assert.False(doc.RootElement.GetProperty("decisions")[0].GetProperty("matched").GetBoolean());
        Assert.Equal("DENY", doc.RootElement.GetProperty("decisions")[0].GetProperty("actions")[0].GetProperty("type").GetString());
    }

    [Fact]
    public async Task API_003_SemanticError()
    {
        var request = new
        {
            Source = "RULE r LANGUAGE 1 WHEN customer.age > \"18\" THEN ALLOW END",
            ContextSchema = new { customer = new { age = "Integer" } },
            Context = new { customer = new { age = 21 } }
        };

        var response = await _client.PostAsJsonAsync("/api/v1/evaluate", request);
        
        Assert.Equal(System.Net.HttpStatusCode.BadRequest, response.StatusCode);
        var content = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(content);
        
        Assert.Equal("error", doc.RootElement.GetProperty("status").GetString());
        Assert.Equal("RF3xxx", doc.RootElement.GetProperty("error_code").GetString());
    }

    [Fact]
    public async Task API_004_DecimalPrecision()
    {
        var request = new
        {
            Source = "RULE r LANGUAGE 1 WHEN invoice.total + 0.2 == 0.3 THEN ALLOW END",
            ContextSchema = new { invoice = new { total = "Decimal" } },
            Context = new { invoice = new { total = 0.1m } }
        };

        var response = await _client.PostAsJsonAsync("/api/v1/evaluate", request);
        response.EnsureSuccessStatusCode();
        
        var content = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(content);
        
        Assert.True(doc.RootElement.GetProperty("decisions")[0].GetProperty("matched").GetBoolean());
    }
}
