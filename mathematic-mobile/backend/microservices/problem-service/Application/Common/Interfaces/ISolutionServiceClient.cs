namespace ProblemService.Application.Common.Interfaces;

public record SolutionServiceRequest(Guid ProblemId, string ProblemText, string? Category, Guid UserId);
public record ProcessImageRequest(Guid ProblemId, string ImagePath, Guid UserId);
public record SolutionServiceResponse(bool Success, Guid ProblemId, string? ExtractedText, string? Solution, List<string>? Steps, double? Confidence, string Message);

public interface ISolutionServiceClient
{
    Task<SolutionServiceResponse?> SolveProblemAsync(SolutionServiceRequest request, CancellationToken cancellationToken = default);
    Task<SolutionServiceResponse?> ProcessImageAsync(ProcessImageRequest request, CancellationToken cancellationToken = default);
}
