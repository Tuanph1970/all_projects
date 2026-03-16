using System.Reflection;
using System.Text;
using FluentValidation;
using MediatR;
using Serilog;
using Serilog.Formatting.Compact;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.ResponseCompression;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using AuthService.Application.Common.Behaviors;
using AuthService.Application.Common.Interfaces;
using AuthService.Infrastructure.Persistence;
using AuthService.Infrastructure.Services;
using AuthService.Middleware;
using AuthService.SeedData;

var builder = WebApplication.CreateBuilder(args);

// ── Structured logging (Serilog) ──────────────────────────────────────────────
// Replaces the default Microsoft console logger with compact JSON output.
// ILogger<T> injection still works — Serilog is the underlying provider.
builder.Host.UseSerilog((ctx, _, cfg) =>
{
    cfg.ReadFrom.Configuration(ctx.Configuration)
       .Enrich.FromLogContext()
       .Enrich.WithMachineName()
       .Enrich.WithProperty("Service", "auth-service")
       .WriteTo.Console(new CompactJsonFormatter());
});

// ── Error tracking (Sentry) ───────────────────────────────────────────────────
// Only activates when SENTRY_DSN is set. Safe to leave unset in development.
// ILogger.LogError() calls are forwarded to Sentry automatically via the
// Serilog → Sentry integration.
builder.WebHost.UseSentry(options =>
{
    options.Dsn = builder.Configuration["Sentry:Dsn"]
                  ?? Environment.GetEnvironmentVariable("SENTRY_DSN")
                  ?? string.Empty;
    options.Environment         = builder.Environment.EnvironmentName;
    options.Release             = typeof(Program).Assembly.GetName().Version?.ToString() ?? "1.0.0";
    options.TracesSampleRate    = builder.Environment.IsProduction() ? 0.1 : 1.0;
    options.MinimumEventLevel   = Microsoft.Extensions.Logging.LogLevel.Error;
    options.AttachStacktrace    = true;
    options.SendDefaultPii      = false; // Never send PII (email, username) to Sentry
});

// Add services to the container.
builder.Services.AddControllers();

// Configure Response Compression
builder.Services.AddResponseCompression(options =>
{
    options.EnableForHttps = true;
    options.Providers.Add<GzipCompressionProvider>();
    options.Providers.Add<BrotliCompressionProvider>();
    options.MimeTypes = new[]
    {
        "text/plain",
        "text/css",
        "application/json",
        "application/xml",
        "text/xml",
        "application/javascript",
        "text/javascript",
        "application/octet-stream"
    };
});

builder.Services.Configure<GzipCompressionProviderOptions>(options =>
{
    options.Level = System.IO.Compression.CompressionLevel.Optimal;
});

builder.Services.Configure<BrotliCompressionProviderOptions>(options =>
{
    options.Level = System.IO.Compression.CompressionLevel.Optimal;
});

// Configure Rate Limiting
builder.Services.Configure<RateLimitOptions>(options =>
{
    options.PermitLimit = 100; // 100 requests per window
    options.WindowInSeconds = 60; // per minute
    options.SegmentsPerWindow = 4;
    options.QueueLimit = 10;
});

// Configure Swagger
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "Mathematics Auth Service",
        Version = "v1",
        Description = "Authentication and User Management Service for Mathematics Solver"
    });

    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Description = "JWT Authorization header using the Bearer scheme",
        Name = "Authorization",
        In = ParameterLocation.Header,
        Type = SecuritySchemeType.ApiKey,
        Scheme = "Bearer"
    });

    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference
                {
                    Type = ReferenceType.SecurityScheme,
                    Id = "Bearer"
                }
            },
            Array.Empty<string>()
        }
    });
});

// Configure Database with retry logic
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
    ?? $"Server={Environment.GetEnvironmentVariable("DB_SERVER") ?? "db"};" +
       $"Port={Environment.GetEnvironmentVariable("DB_PORT") ?? "3306"};" +
       $"Database={Environment.GetEnvironmentVariable("DB_NAME") ?? "MathematicsSolverDb"};" +
       $"User={Environment.GetEnvironmentVariable("DB_USER") ?? "mathematic_user"};" +
       $"Password={Environment.GetEnvironmentVariable("DB_PASSWORD") ?? "Mysql_2025"};";

// Use MySQL 8.0 server version to avoid auto-detection connection issues
var serverVersion = new MySqlServerVersion(new Version(8, 0, 0));

builder.Services.AddDbContext<AuthDbContext>(options =>
    options.UseMySql(connectionString, serverVersion, mysqlOptions =>
    {
        mysqlOptions.MigrationsAssembly(typeof(AuthDbContext).Assembly.FullName);
        mysqlOptions.EnableRetryOnFailure(
            maxRetryCount: 3,
            maxRetryDelay: TimeSpan.FromSeconds(30),
            errorNumbersToAdd: null);
    }));

// Configure JWT Authentication
var jwtSecretKey = builder.Configuration["Jwt:SecretKey"]
    ?? Environment.GetEnvironmentVariable("JWT_SECRET_KEY")
    ?? "your-super-secret-key-change-in-production-minimum-32-chars";

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"] ?? "MathematicsAuth",
            ValidAudience = builder.Configuration["Jwt:Audience"] ?? "MathematicsApp",
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtSecretKey)),
            ClockSkew = TimeSpan.Zero
        };
    });

builder.Services.AddAuthorization();

// Configure Redis Caching
builder.Services.AddStackExchangeRedisCache(options =>
{
    var redisConnection = builder.Configuration.GetConnectionString("Redis")
        ?? Environment.GetEnvironmentVariable("REDIS_CONNECTION")
        ?? "localhost:6379";

    options.Configuration = redisConnection;
    options.ConfigurationOptions = new StackExchange.Redis.ConfigurationOptions
    {
        EndPoints = { redisConnection },
        AbortOnConnectFail = false,
        ConnectTimeout = 5000,
        SyncTimeout = 5000
    };
});

// ----- MediatR + FluentValidation -----
builder.Services.AddMediatR(cfg => cfg.RegisterServicesFromAssembly(Assembly.GetExecutingAssembly()));
builder.Services.AddValidatorsFromAssembly(Assembly.GetExecutingAssembly());
builder.Services.AddTransient(typeof(IPipelineBehavior<,>), typeof(ValidationBehavior<,>));

// ----- Infrastructure services -----
builder.Services.AddScoped<IUnitOfWork, UnitOfWork>();
builder.Services.AddSingleton<IJwtTokenGenerator, JwtTokenGenerator>();
builder.Services.AddSingleton<IPasswordHasher, BCryptPasswordHasher>();
builder.Services.AddScoped<ICacheService, RedisCacheService>();

// Configure Secure CORS
builder.Services.AddSecureCors("AllowSpecificOrigins");

// Configure CORS for development (can be restricted in production)
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// Initialize database
using (var scope = app.Services.CreateScope())
{
    var services = scope.ServiceProvider;
    try
    {
        var context = services.GetRequiredService<AuthDbContext>();
        context.Database.EnsureCreated();
        await DbSeeder.Initialize(services);
    }
    catch (Exception ex)
    {
        var logger = services.GetRequiredService<ILogger<Program>>();
        logger.LogError(ex, "An error occurred while seeding the database.");
    }
}

// Global exception handler — must be FIRST so it wraps all subsequent middleware.
app.UseGlobalExceptionHandler();

// Configure the HTTP request pipeline.
app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "Mathematics Auth Service v1");
    c.RoutePrefix = "swagger";
});

// Use Response Compression
app.UseResponseCompression();

// Use Rate Limiting
app.UseRateLimiting();

// Use Security Headers
app.UseSecurityHeaders();

app.UseCors("AllowAll");
app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

// Health check endpoint
app.MapGet("/health", () => Results.Ok(new
{
    status = "healthy",
    service = "auth-service",
    timestamp = DateTime.UtcNow
}));

var port = Environment.GetEnvironmentVariable("SERVICE_PORT") ?? "8001";
app.Run($"http://0.0.0.0:{port}");
