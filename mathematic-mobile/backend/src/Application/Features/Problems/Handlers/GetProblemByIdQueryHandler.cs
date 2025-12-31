using Application.Common.Exceptions;
using Application.Common.Interfaces;
using Application.DTOs;
using Application.Features.Problems.Queries;
using Microsoft.Extensions.Logging;

namespace Application.Features.Problems.Handlers;

public class GetProblemByIdQueryHandler : IQueryHandler<GetProblemByIdQuery, ProblemDto?>
{
    private readonly IProblemRepository _problemRepository;
    private readonly ILogger<GetProblemByIdQueryHandler> _logger;

    public GetProblemByIdQueryHandler(
        IProblemRepository problemRepository,
        ILogger<GetProblemByIdQueryHandler> logger)
    {
        _problemRepository = problemRepository;
        _logger = logger;
    }

    public async Task<ProblemDto?> Handle(GetProblemByIdQuery request, CancellationToken cancellationToken)
    {
        _logger.LogInformation("Getting problem {ProblemId} for user {UserId}", request.ProblemId, request.UserId);

        var problem = await _problemRepository.GetByIdWithSolutionAsync(request.ProblemId, cancellationToken);

        if (problem == null)
        {
            _logger.LogWarning("Problem {ProblemId} not found", request.ProblemId);
            return null;
        }

        // Verify ownership
        if (problem.UserId != request.UserId)
        {
            _logger.LogWarning("User {UserId} attempted to access problem {ProblemId} owned by {OwnerId}",
                request.UserId, request.ProblemId, problem.UserId);
            throw new UnauthorizedException("You are not authorized to access this problem");
        }

        return new ProblemDto
        {
            Id = problem.Id,
            UserId = problem.UserId,
            ImageUrl = problem.ImageUrl,
            Category = problem.Category,
            Status = problem.Status,
            Description = problem.Description,
            CreatedAt = problem.CreatedAt,
            UpdatedAt = problem.UpdatedAt,
            Solution = problem.Solution != null ? new SolutionDto
            {
                Id = problem.Solution.Id,
                ProblemId = problem.Solution.ProblemId,
                Steps = problem.Solution.Steps,
                Confidence = problem.Solution.Confidence,
                AdditionalNotes = problem.Solution.AdditionalNotes,
                CreatedAt = problem.Solution.CreatedAt
            } : null
        };
    }
}
