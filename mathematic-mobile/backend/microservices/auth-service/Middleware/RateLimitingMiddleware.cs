using System.Collections.Concurrent;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;

namespace AuthService.Middleware;

/// <summary>
/// Rate limiting options configuration
/// </summary>
public class RateLimitOptions
{
    public int PermitLimit { get; set; } = 100;
    public int WindowInSeconds { get; set; } = 60;
    public int SegmentsPerWindow { get; set; } = 4;
    public int QueueLimit { get; set; } = 10;
}

/// <summary>
/// Custom Rate Limiting Middleware for API endpoints
/// Implements sliding window rate limiting with IP-based tracking
/// </summary>
public class RateLimitingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<RateLimitingMiddleware> _logger;
    private readonly RateLimitOptions _options;
    
    // Thread-safe dictionary to track rate limits per IP
    private static readonly ConcurrentDictionary<string, SlidingWindowRateLimiter> _rateLimiters 
        = new ConcurrentDictionary<string, SlidingWindowRateLimiter>();

    public RateLimitingMiddleware(
        RequestDelegate next,
        ILogger<RateLimitingMiddleware> logger,
        IOptions<RateLimitOptions> options)
    {
        _next = next;
        _logger = logger;
        _options = options.Value;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        // Get client IP
        var clientIp = GetClientIp(context);
        
        // Get or create rate limiter for this IP
        var rateLimiter = _rateLimiters.GetOrAdd(clientIp, _ =>
        {
            return new SlidingWindowRateLimiter(new SlidingWindowRateLimiterOptions
            {
                PermitLimit = _options.PermitLimit,
                Window = TimeSpan.FromSeconds(_options.WindowInSeconds),
                SegmentsPerWindow = _options.SegmentsPerWindow,
                QueueLimit = _options.QueueLimit,
                QueueProcessingOrder = QueueProcessingOrder.OldestFirst
            });
        });

        // Try to acquire a permit
        using var lease = await rateLimiter.AcquireAsync(permitCount: 1, context.RequestAborted);
        
        if (!lease.IsAcquired)
        {
            // Rate limit exceeded
            _logger.LogWarning(
                "Rate limit exceeded for IP: {ClientIp} at {Time}",
                clientIp,
                DateTime.UtcNow);

            context.Response.StatusCode = 429; // Too Many Requests
            context.Response.Headers.Add("Retry-After", _options.WindowInSeconds.ToString());
            context.Response.Headers.Add("X-RateLimit-Limit", _options.PermitLimit.ToString());
            context.Response.Headers.Add("X-RateLimit-Remaining", "0");
            
            await context.Response.WriteAsJsonAsync(new
            {
                error = "Too many requests",
                message = $"Rate limit exceeded. Please try again after {_options.WindowInSeconds} seconds.",
                retryAfter = _options.WindowInSeconds,
                timestamp = DateTime.UtcNow
            });
            
            return;
        }

        // Add rate limit headers to successful responses
        context.Response.OnStarting(() =>
        {
            context.Response.Headers.Add("X-RateLimit-Limit", _options.PermitLimit.ToString());
            context.Response.Headers.Add("X-RateLimit-Remaining", 
                (_options.PermitLimit - 1).ToString());
            context.Response.Headers.Add("X-RateLimit-Window", 
                _options.WindowInSeconds.ToString());
            return Task.CompletedTask;
        });

        await _next(context);
    }

    private static string GetClientIp(HttpContext context)
    {
        // Check for X-Forwarded-For header (proxy/load balancer)
        var forwardedFor = context.Request.Headers["X-Forwarded-For"].FirstOrDefault();
        if (!string.IsNullOrEmpty(forwardedFor))
        {
            return forwardedFor.Split(',').First().Trim();
        }

        // Check for X-Real-IP header
        var realIp = context.Request.Headers["X-Real-IP"].FirstOrDefault();
        if (!string.IsNullOrEmpty(realIp))
        {
            return realIp;
        }

        // Fall back to remote IP
        return context.Connection.RemoteIpAddress?.ToString() ?? "unknown";
    }
}

/// <summary>
/// Extension method to add rate limiting middleware
/// </summary>
public static class RateLimitingMiddlewareExtensions
{
    public static IApplicationBuilder UseRateLimiting(
        this IApplicationBuilder builder,
        Action<RateLimitOptions>? configureOptions = null)
    {
        var options = new RateLimitOptions();
        configureOptions?.Invoke(options);
        
        builder.Services.Configure(configureOptions ?? (_ => { }));
        
        return builder.UseMiddleware<RateLimitingMiddleware>();
    }
}
