using Microsoft.AspNetCore.RateLimiting;
using RuleForge.Api.Authorization;
using RuleForge.Api.Middleware;
using System.Threading.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Auth: Register Scope Policies
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("rules:evaluate", policy => policy.Requirements.Add(new ScopeRequirement("rules:evaluate")));
    options.AddPolicy("rules:read", policy => policy.Requirements.Add(new ScopeRequirement("rules:read")));
    options.AddPolicy("rules:write", policy => policy.Requirements.Add(new ScopeRequirement("rules:write")));
    options.AddPolicy("rules:admin", policy => policy.Requirements.Add(new ScopeRequirement("rules:admin")));
});
builder.Services.AddSingleton<IAuthorizationHandler, ScopeHandler>();

// Rate Limiting: 100 req/min per API key
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    options.AddPolicy("apikey", httpContext =>
    {
        var apiKey = httpContext.User.FindFirst("api_key")?.Value ?? "anonymous";
        return RateLimitPartition.GetFixedWindowLimiter(apiKey, _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 100,
            Window = TimeSpan.FromMinutes(1)
        });
    });
});

var app = builder.Build();

app.UseMiddleware<ExceptionMiddleware>();
app.UseMiddleware<ApiKeyMiddleware>();
app.UseRateLimiter();

app.UseSwagger();
app.UseSwaggerUI();

app.MapControllers();

app.Run();

public partial class Program { }
