using Application.Common.Interfaces;
using Domain.Entities;
using Domain.ValueObjects;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using System.Net.Http.Json;
using System.Text.Json;

namespace Infrastructure.Services;

public class MLServiceClient : IMLService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<MLServiceClient> _logger;
    private readonly string _mlServiceBaseUrl;

    public MLServiceClient(
        HttpClient httpClient,
        IConfiguration configuration,
        ILogger<MLServiceClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
        _mlServiceBaseUrl = configuration["MLService:BaseUrl"] ?? "http://localhost:8002";
        _httpClient.BaseAddress = new Uri(_mlServiceBaseUrl);
        _httpClient.Timeout = TimeSpan.FromSeconds(60); // ML processing can take time
    }

    public async Task<Solution?> SolveProblemAsync(Problem problem, CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation("Sending problem {ProblemId} to ML service for solving", problem.Id);

            // Prepare request payload
            var request = new
            {
                image_url = problem.ImageUrl,
                category = problem.Category,
                description = problem.Description
            };

            // Call ML service OCR + Solve endpoint
            var response = await _httpClient.PostAsJsonAsync(
                "/solution/ocr-solve",
                request,
                cancellationToken);

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError("ML service returned error status: {StatusCode}", response.StatusCode);
                return null;
            }

            // Parse response
            var mlResponse = await response.Content.ReadFromJsonAsync<MLSolutionResponse>(cancellationToken);

            if (mlResponse == null || !mlResponse.Success)
            {
                _logger.LogWarning("ML service failed to solve problem {ProblemId}: {Message}",
                    problem.Id, mlResponse?.Message);
                return null;
            }

            // Convert ML response to Solution entity
            var steps = new List<SolutionStep>();
            if (mlResponse.SolutionData?.Steps != null)
            {
                for (int i = 0; i < mlResponse.SolutionData.Steps.Count; i++)
                {
                    var stepText = mlResponse.SolutionData.Steps[i];
                    steps.Add(new SolutionStep(
                        stepNumber: i + 1,
                        description: stepText,
                        formula: null, // ML service doesn't separate formula yet
                        explanation: null
                    ));
                }
            }

            var solution = new Solution(
                problemId: problem.Id,
                steps: steps,
                confidence: (decimal)(mlResponse.SolutionData?.Confidence ?? 0.0)
            );

            if (!string.IsNullOrEmpty(mlResponse.SolutionData?.FinalAnswer))
            {
                solution.AddNotes($"Final Answer: {mlResponse.SolutionData.FinalAnswer}");
            }

            _logger.LogInformation("Problem {ProblemId} solved successfully with {StepCount} steps",
                problem.Id, steps.Count);

            return solution;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling ML service for problem {ProblemId}", problem.Id);
            return null;
        }
    }

    // ML Service Response Models
    private class MLSolutionResponse
    {
        public bool Success { get; set; }
        public string? Message { get; set; }
        public MLSolutionData? SolutionData { get; set; }
        public MLOCRData? OCRData { get; set; }
    }

    private class MLSolutionData
    {
        public string? SolutionText { get; set; }
        public List<string>? Steps { get; set; }
        public string? FinalAnswer { get; set; }
        public double Confidence { get; set; }
    }

    private class MLOCRData
    {
        public string? ExtractedText { get; set; }
        public double Confidence { get; set; }
    }
}
