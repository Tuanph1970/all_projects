using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using AuthService.Data;
using AuthService.Services;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllers();

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
    options.UseMySql(connectionString, serverVersion));

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

// Register Services
builder.Services.AddScoped<IJwtService, JwtService>();
builder.Services.AddScoped<IAuthenticationService, AuthenticationService>();

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

// Configure the HTTP request pipeline.
app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "Mathematics Auth Service v1");
    c.RoutePrefix = "swagger";
});

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

// Apply migrations on startup with retry logic
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AuthDbContext>();
    var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();

    var maxRetries = 10;
    var delay = TimeSpan.FromSeconds(5);

    for (int i = 0; i < maxRetries; i++)
    {
        try
        {
            logger.LogInformation("Attempting database connection (attempt {Attempt}/{MaxRetries})...", i + 1, maxRetries);
            db.Database.EnsureCreated();
            logger.LogInformation("Database connection successful and tables created");
            break;
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Database connection failed (attempt {Attempt}/{MaxRetries})", i + 1, maxRetries);
            if (i == maxRetries - 1)
            {
                logger.LogError("Failed to connect to database after {MaxRetries} attempts", maxRetries);
                throw;
            }
            Thread.Sleep(delay);
        }
    }
}

var port = Environment.GetEnvironmentVariable("SERVICE_PORT") ?? "8001";
app.Run($"http://0.0.0.0:{port}");
