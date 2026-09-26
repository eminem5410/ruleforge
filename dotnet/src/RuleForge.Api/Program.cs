using System.IdentityModel.Tokens.Jwt;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.IdentityModel.Tokens;
using RuleForge.Api.Authorization;
using RuleForge.Api.Middleware;
using System.Text;
using System.Threading.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// 1. Auth: Dual Authentication (ApiKey + JwtBearer)
builder.Services.AddAuthentication()
    .AddScheme<AuthenticationSchemeOptions, ApiKeyAuthenticationHandler>("ApiKey", null)
    .AddJwtBearer("JwtBearer", options =>
    {
        var jwtConfig = builder.Configuration.GetSection("RuleForge:Jwt");
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = jwtConfig["Issuer"],
            ValidAudience = jwtConfig["Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtConfig["SigningKey"]!)),
            NameClaimType = "sub",
            RoleClaimType = "scope"
        };
    });

// 2. Auth: Register Scope Policies (Accept both schemes)
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("rules:evaluate", policy => 
    {
        policy.Requirements.Add(new ScopeRequirement("rules:evaluate"));
        policy.AddAuthenticationSchemes("ApiKey", "JwtBearer");
    });
    options.AddPolicy("rules:read", policy => 
    {
        policy.Requirements.Add(new ScopeRequirement("rules:read"));
        policy.AddAuthenticationSchemes("ApiKey", "JwtBearer");
    });
    options.AddPolicy("rules:write", policy => 
    {
        policy.Requirements.Add(new ScopeRequirement("rules:write"));
        policy.AddAuthenticationSchemes("ApiKey", "JwtBearer");
    });
    options.AddPolicy("rules:admin", policy => 
    {
        policy.Requirements.Add(new ScopeRequirement("rules:admin"));
        policy.AddAuthenticationSchemes("ApiKey", "JwtBearer");
    });
});
builder.Services.AddSingleton<IAuthorizationHandler, ScopeHandler>();

// 3. Rate Limiting: 100 req/min per identity (Extracted from raw header)
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    
    options.OnRejected = async (context, cancellationToken) =>
    {
        context.HttpContext.Response.StatusCode = StatusCodes.Status429TooManyRequests;
        context.HttpContext.Response.ContentType = "application/json";
        
        if (context.Lease.TryGetMetadata("RETRY_AFTER", out var retryAfter) && retryAfter is TimeSpan timeSpan)
        {
            context.HttpContext.Response.Headers["Retry-After"] = ((int)Math.Ceiling(timeSpan.TotalSeconds)).ToString();
        }
        
        await context.HttpContext.Response.WriteAsync("{\"status\":\"error\",\"error_code\":\"RATE_LIMIT_EXCEEDED\"}");
    };
    
    options.AddPolicy("apikey", httpContext =>
    {
        var authHeader = httpContext.Request.Headers.Authorization.ToString();
        string identity = "anonymous";
        
        if (authHeader.StartsWith("ApiKey ", StringComparison.OrdinalIgnoreCase))
        {
            identity = authHeader.Substring("ApiKey ".Length).Trim();
        }
        else if (authHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            var token = authHeader.Substring("Bearer ".Length).Trim();
            try
            {
                // Parse JWT payload to extract 'sub' without validating signature (Auth middleware will validate it next)
                var jwt = new JwtSecurityTokenHandler().ReadJwtToken(token);
                var subClaim = jwt.Claims.FirstOrDefault(c => c.Type == "sub");
                if (subClaim != null && !string.IsNullOrEmpty(subClaim.Value))
                {
                    identity = subClaim.Value;
                }
            }
            catch
            {
                // Token is malformed, Auth middleware will reject it. Use anonymous bucket.
            }
        }
                     
        return RateLimitPartition.GetFixedWindowLimiter(identity, _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 100,
            Window = TimeSpan.FromMinutes(1)
        });
    });
});

var app = builder.Build();

app.UseMiddleware<ExceptionMiddleware>();

app.UseAuthentication();
app.UseRateLimiter();
app.UseAuthorization();

app.UseSwagger();
app.UseSwaggerUI();

app.MapControllers();

app.Run();

public partial class Program { }
