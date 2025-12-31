using Application.Common.Exceptions;
using System.Diagnostics;
using System.Text.Json;

namespace Presentation.Middleware;

public class ExceptionHandlingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ExceptionHandlingMiddleware> _logger;

    public ExceptionHandlingMiddleware(RequestDelegate next, ILogger<ExceptionHandlingMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            await HandleExceptionAsync(context, ex);
        }
    }

    private async Task HandleExceptionAsync(HttpContext context, Exception exception)
    {
        _logger.LogError(exception, "An unhandled exception has occurred: {Message}", exception.Message);

        var response = exception switch
        {
            ValidationException validationException => CreateValidationErrorResponse(validationException),
            UnauthorizedException => CreateErrorResponse(StatusCodes.Status401Unauthorized, "Unauthorized", "Invalid credentials or access denied"),
            NotFoundException => CreateErrorResponse(StatusCodes.Status404NotFound, "Not Found", exception.Message),
            ArgumentNullException => CreateErrorResponse(StatusCodes.Status400BadRequest, "Bad Request", "Required parameter is missing"),
            ArgumentException => CreateErrorResponse(StatusCodes.Status400BadRequest, "Bad Request", exception.Message),
            _ => CreateErrorResponse(StatusCodes.Status500InternalServerError, "Internal Server Error", "An error occurred processing your request")
        };

        context.Response.StatusCode = response.StatusCode;
        context.Response.ContentType = "application/json";

        await context.Response.WriteAsync(JsonSerializer.Serialize(response.Body, new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        }));
    }

    private ErrorResponse CreateErrorResponse(int statusCode, string title, string detail)
    {
        return new ErrorResponse
        {
            StatusCode = statusCode,
            Body = new
            {
                Title = title,
                Detail = detail,
                Status = statusCode,
                TraceId = Activity.Current?.Id ?? "unknown"
            }
        };
    }

    private ErrorResponse CreateValidationErrorResponse(ValidationException validationException)
    {
        return new ErrorResponse
        {
            StatusCode = StatusCodes.Status400BadRequest,
            Body = new
            {
                Title = "Validation Error",
                Detail = "One or more validation errors occurred",
                Status = StatusCodes.Status400BadRequest,
                TraceId = Activity.Current?.Id ?? "unknown",
                Errors = validationException.Errors
            }
        };
    }

    private record ErrorResponse
    {
        public int StatusCode { get; init; }
        public object Body { get; init; } = null!;
    }
}