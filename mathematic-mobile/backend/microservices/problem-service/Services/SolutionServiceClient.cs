using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Polly;
using Polly.Retry;

namespace ProblemService.Services;

/// <summary>
/// DTOs for Solution Service communication
/// </summary>
public class SolutionServiceRequest
{
    public int ProblemId { get; set; }
    public string ProblemText { get; set; } = string.Empty;
    public string? Category { get; set; }
    public int UserId { get; set; }
}

public class SolutionServiceResponse
{
    public bool Success { get; set; }
    public int ProblemId { get; set; }
    public string? ExtractedText { get; set; }
    public string? Solution { get; set; }
    public List<string>? Steps { get; set; }
    public double? Confidence { get; set; }
    public string Message { get; set; } = string.Empty;
}

public class ProcessImageRequest
{
    public int ProblemId { get; set; }
    public string ImagePath { get; set; } = string.Empty;
    public int UserId { get; set; }
}

/// <summary>
/// Resilient HTTP client for communicating with the Solution Service.
/// Implements retry logic with Polly for handling transient failures.
/// </summary>
public interface ISolutionServiceClient
{
    /// <summary>
    /// Send problem to Solution Service for solving
    /// </summary>
    Task<SolutionServiceResponse?> SolveProblemAsync(SolutionServiceRequest request, CancellationToken cancellationToken = default);

    /// <summary>
    /// Send image to Solution Service for OCR processing
    /// </summary>
    Task<SolutionServiceResponse?> ProcessImageAsync(ProcessImageRequest request, CancellationToken cancellationToken = default);
}

public class SolutionServiceClient : ISolutionServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<SolutionServiceClient> _logger;
    private readonly IConfiguration _configuration;
    private readonly string _serviceToken;
    private readonly AsyncRetryPolicy<HttpResponseMessage> _retryPolicy;

    public SolutionServiceClient(
        HttpClient httpClient,
        ILogger<SolutionServiceClient> logger,
        IConfiguration configuration)
    {
        _httpClient = httpClient;
        _logger = logger;
        _configuration = configuration;
        _serviceToken = configuration["InternalServiceToken"] ?? Environment.GetEnvironmentVariable("INTERNAL_SERVICE_TOKEN") ?? "internal-service-token";

        // Configure retry policy with Polly
        _retryPolicy = HttpPolicyExtensions
            .HandleTransientHttpError()
            .OrResult(msg => msg.StatusCode == HttpStatusCode.TooManyRequests)
            .WaitAndRetryAsync(
                retryCount: 3,
                sleepDurationProvider: retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)), // Exponential backoff: 2s, 4s, 8s
                onRetry: (outcome, timespan, retryAttempt, context) =>
                {
                    _logger.LogWarning(
                        outcome.Exception,
                        "Retry attempt {RetryAttempt} after {Delay}s due to: {Reason}",
                        retryAttempt,
                        timespan.TotalSeconds,
                        outcome.Result?.StatusCode.ToString() ?? outcome.Exception?.Message ?? "Unknown");
                }
            );

        _logger.LogInformation("Solution Service Client initialized with BaseAddress: {BaseAddress}", _httpClient.BaseAddress);
    }

    /// <summary>
    /// Send problem to Solution Service for solving with retry logic
    /// </summary>
    public async Task<SolutionServiceResponse?> SolveProblemAsync(SolutionServiceRequest request, CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation("Sending problem {ProblemId} to Solution Service for solving", request.ProblemId);

            var response = await ExecuteWithRetryAsync(
                async () => await _httpClient.PostAsJsonAsync("/api/v1/solutions/solve", request, cancellationToken),
                "SolveProblem"
            );

            if (response.IsSuccessStatusCode)
            {
                var result = await response.Content.ReadFromJsonAsync<SolutionServiceResponse>(cancellationToken: cancellationToken);
                _logger.LogInformation("Problem {ProblemId} solved successfully. Confidence: {Confidence}", 
                    request.ProblemId, result?.Confidence);
                return result;
            }

            var errorContent = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogError("Solution Service returned error for problem {ProblemId}: {StatusCode} - {Error}", 
                request.ProblemId, response.StatusCode, errorContent);

            return new SolutionServiceResponse
            {
                Success = false,
                ProblemId = request.ProblemId,
                Message = $"Solution Service error: {response.StatusCode}"
            };
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            _logger.LogWarning("SolveProblem request cancelled for problem {ProblemId}", request.ProblemId);
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to solve problem {ProblemId} via Solution Service", request.ProblemId);
            return new SolutionServiceResponse
            {
                Success = false,
                ProblemId = request.ProblemId,
                Message = $"Solution Service communication failed: {ex.Message}"
            };
        }
    }

    /// <summary>
    /// Send image to Solution Service for OCR processing with retry logic
    /// </summary>
    public async Task<SolutionServiceResponse?> ProcessImageAsync(ProcessImageRequest request, CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation("Sending image for problem {ProblemId} to Solution Service for OCR processing", request.ProblemId);

            var response = await ExecuteWithRetryAsync(
                async () => await _httpClient.PostAsJsonAsync("/api/v1/solutions/process-image", request, cancellationToken),
                "ProcessImage"
            );

            if (response.IsSuccessStatusCode)
            {
                var result = await response.Content.ReadFromJsonAsync<SolutionServiceResponse>(cancellationToken: cancellationToken);
                _logger.LogInformation("Image for problem {ProblemId} processed successfully. Extracted text length: {Length}", 
                    request.ProblemId, result?.ExtractedText?.Length);
                return result;
            }

            var errorContent = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogError("Solution Service returned error for image processing {ProblemId}: {StatusCode} - {Error}", 
                request.ProblemId, response.StatusCode, errorContent);

            return new SolutionServiceResponse
            {
                Success = false,
                ProblemId = request.ProblemId,
                Message = $"Solution Service error: {response.StatusCode}"
            };
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            _logger.LogWarning("ProcessImage request cancelled for problem {ProblemId}", request.ProblemId);
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to process image for problem {ProblemId} via Solution Service", request.ProblemId);
            return new SolutionServiceResponse
            {
                Success = false,
                ProblemId = request.ProblemId,
                Message = $"Solution Service communication failed: {ex.Message}"
            };
        }
    }

    /// <summary>
    /// Execute HTTP request with retry policy
    /// </summary>
    private async Task<HttpResponseMessage> ExecuteWithRetryAsync(
        Func<Task<HttpResponseMessage>> action,
        string operationName)
    {
        try
        {
            // Add service token header
            _httpClient.DefaultRequestHeaders.Remove("X-Service-Token");
            _httpClient.DefaultRequestHeaders.Add("X-Service-Token", _serviceToken);

            // Execute with retry policy
            var response = await _retryPolicy.ExecuteAsync(async () =>
            {
                var result = await action();
                return result;
            });

            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "{OperationName} failed after all retry attempts", operationName);
            throw;
        }
    }
}

/// <summary>
/// Extension methods for registering Solution Service Client
/// </summary>
public static class SolutionServiceClientExtensions
{
    public static IServiceCollection AddSolutionServiceClient(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        var solutionServiceUrl = configuration["SolutionService:BaseUrl"] 
            ?? Environment.GetEnvironmentVariable("SOLUTION_SERVICE_URL") 
            ?? "http://solution-service:8003";

        services.AddHttpClient<ISolutionServiceClient, SolutionServiceClient>((serviceProvider, client) =>
        {
            client.BaseAddress = new Uri(solutionServiceUrl);
            client.DefaultRequestHeaders.Add("Accept", "application/json");
            client.Timeout = TimeSpan.FromSeconds(60); // Longer timeout for ML processing
        })
        .AddTransientHttpErrorPolicy(policy => policy.WaitAndRetryAsync(
            retryCount: 3,
            sleepDurationProvider: retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)),
            onRetry: (outcome, timespan, retryAttempt, context) =>
            {
                var logger = serviceProvider.GetRequiredService<ILogger<SolutionServiceClient>>();
                logger.LogWarning(
                    "Retry {RetryAttempt} after {Delay}s: {StatusCode}",
                    retryAttempt,
                    timespan.TotalSeconds,
                    outcome.Result?.StatusCode.ToString() ?? "Error");
            }
        ));

        return services;
    }
}
