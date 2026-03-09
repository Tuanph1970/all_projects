using System.Net;
using System.Net.Http.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Polly;
using Polly.Retry;
using ProblemService.Application.Common.Interfaces;

namespace ProblemService.Infrastructure.ExternalServices;

public class SolutionServiceClient : ISolutionServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<SolutionServiceClient> _logger;
    private readonly string _serviceToken;
    private readonly AsyncRetryPolicy<HttpResponseMessage> _retryPolicy;

    public SolutionServiceClient(
        HttpClient httpClient,
        ILogger<SolutionServiceClient> logger,
        IConfiguration configuration)
    {
        _httpClient = httpClient;
        _logger = logger;
        _serviceToken = configuration["InternalServiceToken"]
            ?? Environment.GetEnvironmentVariable("INTERNAL_SERVICE_TOKEN")
            ?? "internal-service-token";

        _retryPolicy = Policy
            .Handle<HttpRequestException>()
            .OrResult<HttpResponseMessage>(msg =>
                msg.StatusCode >= HttpStatusCode.InternalServerError ||
                msg.StatusCode == HttpStatusCode.RequestTimeout ||
                msg.StatusCode == HttpStatusCode.TooManyRequests)
            .WaitAndRetryAsync(
                retryCount: 3,
                sleepDurationProvider: attempt => TimeSpan.FromSeconds(Math.Pow(2, attempt)),
                onRetry: (outcome, timespan, attempt, _) =>
                    _logger.LogWarning(
                        outcome.Exception,
                        "Retry attempt {Attempt} after {Delay}s: {Reason}",
                        attempt, timespan.TotalSeconds,
                        outcome.Result?.StatusCode.ToString() ?? outcome.Exception?.Message));
    }

    public async Task<SolutionServiceResponse?> SolveProblemAsync(SolutionServiceRequest request, CancellationToken cancellationToken = default)
    {
        try
        {
            var response = await ExecuteWithRetryAsync(
                () => _httpClient.PostAsJsonAsync("/api/v1/solutions/solve", request, cancellationToken));

            if (response.IsSuccessStatusCode)
                return await response.Content.ReadFromJsonAsync<SolutionServiceResponse>(cancellationToken: cancellationToken);

            _logger.LogError("Solution Service error for problem {ProblemId}: {StatusCode}", request.ProblemId, response.StatusCode);
            return new SolutionServiceResponse(false, request.ProblemId, null, null, null, null, $"Solution Service error: {response.StatusCode}");
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to solve problem {ProblemId}", request.ProblemId);
            return new SolutionServiceResponse(false, request.ProblemId, null, null, null, null, $"Communication failed: {ex.Message}");
        }
    }

    public async Task<SolutionServiceResponse?> ProcessImageAsync(ProcessImageRequest request, CancellationToken cancellationToken = default)
    {
        try
        {
            var response = await ExecuteWithRetryAsync(
                () => _httpClient.PostAsJsonAsync("/api/v1/solutions/process-image", request, cancellationToken));

            if (response.IsSuccessStatusCode)
                return await response.Content.ReadFromJsonAsync<SolutionServiceResponse>(cancellationToken: cancellationToken);

            _logger.LogError("Solution Service error for image {ProblemId}: {StatusCode}", request.ProblemId, response.StatusCode);
            return new SolutionServiceResponse(false, request.ProblemId, null, null, null, null, $"Solution Service error: {response.StatusCode}");
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to process image for problem {ProblemId}", request.ProblemId);
            return new SolutionServiceResponse(false, request.ProblemId, null, null, null, null, $"Communication failed: {ex.Message}");
        }
    }

    private async Task<HttpResponseMessage> ExecuteWithRetryAsync(Func<Task<HttpResponseMessage>> action)
    {
        _httpClient.DefaultRequestHeaders.Remove("X-Service-Token");
        _httpClient.DefaultRequestHeaders.Add("X-Service-Token", _serviceToken);
        return await _retryPolicy.ExecuteAsync(async () => await action());
    }
}

public static class SolutionServiceClientExtensions
{
    public static IServiceCollection AddSolutionServiceClient(this IServiceCollection services, IConfiguration configuration)
    {
        var url = configuration["SolutionService:BaseUrl"]
            ?? Environment.GetEnvironmentVariable("SOLUTION_SERVICE_URL")
            ?? "http://solution-service:8003";

        services.AddHttpClient<ISolutionServiceClient, SolutionServiceClient>(client =>
        {
            client.BaseAddress = new Uri(url);
            client.DefaultRequestHeaders.Add("Accept", "application/json");
            client.Timeout = TimeSpan.FromSeconds(60);
        });

        return services;
    }
}
