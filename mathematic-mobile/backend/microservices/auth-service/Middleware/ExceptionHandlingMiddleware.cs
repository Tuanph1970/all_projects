using System.Diagnostics;
using System.Net;
using System.Text.Json;
using AuthService.Application.Common.Exceptions;

namespace AuthService.Middleware;

/// <summary>
/// Global exception handling middleware.
/// Catches all unhandled exceptions, logs them, and returns a consistent
/// JSON error response without leaking internal stack traces.
/// Must be registered first in the middleware pipeline.
/// </summary>
public class ExceptionHandlingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ExceptionHandlingMiddleware> _logger;
    private readonly IHostEnvironment _env;

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public ExceptionHandlingMiddleware(
        RequestDelegate next,
        ILogger<ExceptionHandlingMiddleware> logger,
        IHostEnvironment env)
    {
        _next = next;
        _logger = logger;
        _env = env;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested)
        {
            // Client disconnected — not an application error, ignore silently.
            context.Response.StatusCode = 499;
        }
        catch (AppValidationException valEx)
        {
            await HandleValidationExceptionAsync(context, valEx);
        }
        catch (Exception ex)
        {
            await HandleExceptionAsync(context, ex);
        }
    }

    private async Task HandleValidationExceptionAsync(HttpContext context, AppValidationException exception)
    {
        if (context.Response.HasStarted)
        {
            _logger.LogWarning("Response already started; cannot write validation error body.");
            return;
        }

        context.Response.StatusCode  = (int)HttpStatusCode.BadRequest;
        context.Response.ContentType = "application/json";

        var body = new ValidationErrorResponse(
            Success:   false,
            Status:    (int)HttpStatusCode.BadRequest,
            Title:     "Validation Error",
            Detail:    exception.Message,
            Errors:    exception.Errors,
            TraceId:   Activity.Current?.Id ?? context.TraceIdentifier
        );

        await context.Response.WriteAsync(JsonSerializer.Serialize(body, _jsonOptions));
    }

    private async Task HandleExceptionAsync(HttpContext context, Exception exception)
    {
        _logger.LogError(
            exception,
            "Unhandled exception on {Method} {Path}. TraceId: {TraceId}",
            context.Request.Method,
            context.Request.Path,
            Activity.Current?.Id ?? context.TraceIdentifier);

        var (statusCode, title) = exception switch
        {
            UnauthorizedException               => (HttpStatusCode.Unauthorized,        "Unauthorized"),
            NotFoundException                   => (HttpStatusCode.NotFound,            "Not Found"),
            UnauthorizedAccessException         => (HttpStatusCode.Unauthorized,        "Unauthorized"),
            ArgumentNullException               => (HttpStatusCode.BadRequest,          "Bad Request"),
            ArgumentException                   => (HttpStatusCode.BadRequest,          "Bad Request"),
            KeyNotFoundException                => (HttpStatusCode.NotFound,            "Not Found"),
            InvalidOperationException           => (HttpStatusCode.UnprocessableEntity, "Invalid Operation"),
            TimeoutException                    => (HttpStatusCode.GatewayTimeout,      "Request Timed Out"),
            _                                   => (HttpStatusCode.InternalServerError, "Internal Server Error")
        };

        if (context.Response.HasStarted)
        {
            _logger.LogWarning("Response already started; cannot write error body.");
            return;
        }

        context.Response.StatusCode  = (int)statusCode;
        context.Response.ContentType = "application/json";

        var body = new ErrorResponse(
            Success:    false,
            Status:     (int)statusCode,
            Title:      title,
            Detail:     _env.IsDevelopment() ? exception.Message : "An unexpected error occurred. Please try again.",
            TraceId:    Activity.Current?.Id ?? context.TraceIdentifier,
            // Expose stack trace only in Development to aid debugging.
            StackTrace: _env.IsDevelopment() ? exception.StackTrace : null
        );

        await context.Response.WriteAsync(JsonSerializer.Serialize(body, _jsonOptions));
    }
}

internal record ErrorResponse(
    bool    Success,
    int     Status,
    string  Title,
    string  Detail,
    string? TraceId,
    string? StackTrace
);

internal record ValidationErrorResponse(
    bool                            Success,
    int                             Status,
    string                          Title,
    string                          Detail,
    IDictionary<string, string[]>   Errors,
    string?                         TraceId
);

public static class ExceptionHandlingMiddlewareExtensions
{
    /// <summary>
    /// Registers the global exception handler. Call this before all other middleware.
    /// </summary>
    public static IApplicationBuilder UseGlobalExceptionHandler(this IApplicationBuilder builder)
        => builder.UseMiddleware<ExceptionHandlingMiddleware>();
}
