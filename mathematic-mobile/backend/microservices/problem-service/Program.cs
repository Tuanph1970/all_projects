using System.Reflection;
using System.Text;
using FluentValidation;
using MediatR;
using Serilog;
using Serilog.Formatting.Compact;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using ProblemService.Application.Common.Behaviors;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Infrastructure.ExternalServices;
using ProblemService.Infrastructure.Persistence;
using ProblemService.Middleware;
using ProblemService.SeedData;

var builder = WebApplication.CreateBuilder(args);

// ── Structured logging (Serilog) ──────────────────────────────────────────────
builder.Host.UseSerilog((ctx, _, cfg) =>
{
    cfg.ReadFrom.Configuration(ctx.Configuration)
       .Enrich.FromLogContext()
       .Enrich.WithMachineName()
       .Enrich.WithProperty("Service", "problem-service")
       .WriteTo.Console(new CompactJsonFormatter());
});

// ── Error tracking (Sentry) ───────────────────────────────────────────────────
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
    options.SendDefaultPii      = false;
});

builder.Services.AddControllers();

// Configure Swagger
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "Mathematics Problem Service",
        Version = "v1",
        Description = "Problem Management Service for Mathematics Solver"
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

// Configure Database
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
    ?? $"Server={Environment.GetEnvironmentVariable("DB_SERVER") ?? "db"};" +
       $"Port={Environment.GetEnvironmentVariable("DB_PORT") ?? "3306"};" +
       $"Database={Environment.GetEnvironmentVariable("DB_NAME") ?? "MathematicsSolverDb"};" +
       $"User={Environment.GetEnvironmentVariable("DB_USER") ?? "mathematic_user"};" +
       $"Password={Environment.GetEnvironmentVariable("DB_PASSWORD") ?? "Mysql_2025"};";

var serverVersion = new MySqlServerVersion(new Version(8, 0, 0));

builder.Services.AddDbContext<ProblemDbContext>(options =>
    options.UseMySql(connectionString, serverVersion, mysqlOptions =>
    {
        mysqlOptions.MigrationsAssembly(typeof(ProblemDbContext).Assembly.FullName);
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

// ----- MediatR + FluentValidation -----
builder.Services.AddMediatR(cfg => cfg.RegisterServicesFromAssembly(Assembly.GetExecutingAssembly()));
builder.Services.AddValidatorsFromAssembly(Assembly.GetExecutingAssembly());
builder.Services.AddTransient(typeof(IPipelineBehavior<,>), typeof(ValidationBehavior<,>));

// ----- Infrastructure services -----
builder.Services.AddScoped<IUnitOfWork, UnitOfWork>();

// Register Solution Service Client
builder.Services.AddSolutionServiceClient(builder.Configuration);

// Configure CORS
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
        var context = services.GetRequiredService<ProblemDbContext>();
        context.Database.EnsureCreated();
        await DbSeeder.Initialize(services);
    }
    catch (Exception ex)
    {
        var logger = services.GetRequiredService<ILogger<Program>>();
        logger.LogError(ex, "An error occurred while seeding the database.");
    }
}

// Global exception handler — must be FIRST
app.UseGlobalExceptionHandler();

app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "Mathematics Problem Service v1");
    c.RoutePrefix = "swagger";
});

app.UseCors("AllowAll");

// Serve uploaded files
var uploadPath = Environment.GetEnvironmentVariable("STORAGE_UPLOAD_PATH") ?? "/app/uploads";
Directory.CreateDirectory(uploadPath);
app.UseStaticFiles(new StaticFileOptions
{
    FileProvider = new Microsoft.Extensions.FileProviders.PhysicalFileProvider(uploadPath),
    RequestPath = "/uploads"
});

app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

app.MapGet("/health", () => Results.Ok(new
{
    status = "healthy",
    service = "problem-service",
    timestamp = DateTime.UtcNow
}));

var port = Environment.GetEnvironmentVariable("SERVICE_PORT") ?? "8002";
app.Run($"http://0.0.0.0:{port}");
