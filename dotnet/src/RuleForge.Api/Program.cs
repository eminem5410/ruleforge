using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.RateLimiting;
using RuleForge.Api.Authorization;
using RuleForge.Api.Middleware;
using System.Threading.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// 1. Auth: Register the custom ApiKey Authentication Handler
builder.Services.AddAuthentication("ApiKey")
    .AddScheme<AuthenticationSchemeOptions, ApiKeyAuthenticationHandler>("ApiKey", null);

// 2. Auth: Register Scope Policies
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("rules:evaluate", policy => policy.Requirements.Add(new ScopeRequirement("rules:evaluate")));
    options.AddPolicy("rules:read", policy => policy.Requirements.Add(new ScopeRequirement("rules:read")));
    options.AddPolicy("rules:write", policy => policy.Requirements.Add(new ScopeRequirement("rules:write")));
    options.AddPolicy("rules:admin", policy => policy.Requirements.Add(new ScopeRequirement("rules:admin")));
});
builder.Services.AddSingleton<IAuthorizationHandler, ScopeHandler>();

// 3. Rate Limiting: 100 req/min per API key
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    
    // Intercept rejection to add Retry-After header
    options.OnRejected = async (context, cancellationToken) =>
    {
        context.HttpContext.Response.StatusCode = StatusCodes.Status429TooManyRequests;
        context.HttpContext.Response.ContentType = "application/json";
        
        if (context.Lease.TryGetMetadata("RETRY_AFTER", out var retryAfter))
        {
            context.HttpContext.Response.Headers["Retry-After"] = ((int)retryAfter.TotalSeconds).ToString();
        }
        
        await context.HttpContext.Response.WriteAsync("{\"status\":\"error\",\"error_code\":\"RATE_LIMIT_EXCEEDED\"}");
    };
    
    options.AddPolicy("apikey", httpContext =>
    {
        var apiKey = httpContext.User.FindFirst("api_key_id")?.Value ?? "anonymous";
        return RateLimitPartition.GetFixedWindowLimiter(apiKey, _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 100,
            Window = TimeSpan.FromMinutes(1)
        });
    });
});

var app = builder.Build();

app.UseMiddleware<ExceptionMiddleware>();

// IMPORTANT: Order matters. UseAuthentication must come before UseAuthorization
app.UseAuthentication();
app.UseRateLimiter();
app.UseAuthorization();

app.UseSwagger();
app.UseSwaggerUI();

app.MapControllers();

app.Run();

public partial class Program { }
