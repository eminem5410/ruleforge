using System.IdentityModel.Tokens.Jwt;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using RuleForge.Api.Authorization;
using RuleForge.Api.Middleware;
using System.Text;
using System.Threading.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();

// 1. Swagger con Dual Auth
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo { Title = "RuleForge API", Version = "v1" });

    // Scheme 1: ApiKey
    c.AddSecurityDefinition("ApiKey", new OpenApiSecurityScheme
    {
        Type = SecuritySchemeType.ApiKey,
        In = ParameterLocation.Header,
        Name = "Authorization",
        Description = "API Key Auth. Format: 'ApiKey rf_live_...'"
    });

    // Scheme 2: JWT Bearer
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Type = SecuritySchemeType.Http,
        Scheme = "bearer",
        BearerFormat = "JWT",
        Description = "JWT Auth. Format: 'Bearer eyJ...'"
    });

    // Aplicar ambos a todos los endpoints
    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "ApiKey" }
            },
            Array.Empty<string>()
        },
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "Bearer" }
            },
            Array.Empty<string>()
        }
    });
});

// 2. Auth: Dual Authentication (ApiKey + JwtBearer)
builder.Services.AddAuthentication()
    .AddScheme<AuthenticationSchemeOptions, ApiKeyAuthenticationHandler>("ApiKey", null)
    .AddJwtBearer("JwtBearer", options =>
    {
        // Evitar mapeos mágicos de claims de Microsoft
        JwtSecurityTokenHandler.DefaultInboundClaimTypeMap.Clear();
        options.MapInboundClaims = false;

        var jwtConfig = builder.Configuration.GetSection("RuleForge:Jwt");
        
        // Leer Signing Key desde Env Var primero, fallback a appsettings para Dev
        var signingKey = Environment.GetEnvironmentVariable("RULEFORGE_JWT_SIGNING_KEY") ?? jwtConfig["SigningKey"];

        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = jwtConfig["Issuer"],
            ValidAudience = jwtConfig["Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(signingKey!)),
            NameClaimType = "sub",
            RoleClaimType = "scope"
        };
    });

// 3. Auth: Register Scope Policies
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

// 4. Rate Limiting: 100 req/min per identity (api_key_id or sub)
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
            var token = authHeader.Substring("ApiKey ".Length).Trim();
            // Para API Key, usamos el token completo solo para el Rate Limit interno, 
            // pero el Handler ya lo mapeó a un ID seguro para logs.
            identity = token; 
        }
        else if (authHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            var token = authHeader.Substring("Bearer ".Length).Trim();
            try
            {
                var jwt = new JwtSecurityTokenHandler().ReadJwtToken(token);
                var subClaim = jwt.Claims.FirstOrDefault(c => c.Type == "sub");
                if (subClaim != null && !string.IsNullOrEmpty(subClaim.Value))
                {
                    identity = subClaim.Value;
                }
            }
            catch { }
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
