using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using System.Threading.Tasks;

namespace AuthService.Middleware;

/// <summary>
/// Security Headers Middleware
/// Adds security-related HTTP headers to prevent common web vulnerabilities
/// </summary>
public class SecurityHeadersMiddleware
{
    private readonly RequestDelegate _next;

    public SecurityHeadersMiddleware(RequestDelegate next)
    {
        _next = next;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        // Prevent clickjacking attacks
        context.Response.Headers.Add("X-Frame-Options", "DENY");
        
        // Enable XSS filter in browsers
        context.Response.Headers.Add("X-Content-Type-Options", "nosniff");
        context.Response.Headers.Add("X-XSS-Protection", "1; mode=block");
        
        // Control referrer information
        context.Response.Headers.Add("Referrer-Policy", "strict-origin-when-cross-origin");
        
        // Content Security Policy
        context.Response.Headers.Add(
            "Content-Security-Policy", 
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'");
        
        // Permissions Policy
        context.Response.Headers.Add(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()");

        await _next(context);
    }
}

/// <summary>
/// CORS Configuration Helper
/// </summary>
public static class CorsConfiguration
{
    public static void AddSecureCors(this IServiceCollection services, string policyName, Action<CorsOptions>? configure = null)
    {
        services.AddCors(options =>
        {
            options.AddPolicy(policyName, builder =>
            {
                // In production, replace with specific origins
                var allowedOrigins = Environment.GetEnvironmentVariable("CORS_ALLOWED_ORIGINS")
                    ?.Split(',', StringSplitOptions.RemoveEmptyEntries)
                    ?? new[] { "http://localhost:19002", "http://localhost:3000" };

                builder
                    .WithOrigins(allowedOrigins)
                    .AllowAnyMethod()
                    .AllowAnyHeader()
                    .AllowCredentials()
                    .WithExposedHeaders(
                        "X-RateLimit-Limit",
                        "X-RateLimit-Remaining",
                        "X-RateLimit-Window",
                        "X-Request-Id")
                    .SetPreflightMaxAge(TimeSpan.FromMinutes(30));

                configure?.Invoke(options);
            });
        });
    }
}

/// <summary>
/// Extension method to add security headers
/// </summary>
public static class SecurityHeadersMiddlewareExtensions
{
    public static IApplicationBuilder UseSecurityHeaders(this IApplicationBuilder builder)
    {
        return builder.UseMiddleware<SecurityHeadersMiddleware>();
    }
}
