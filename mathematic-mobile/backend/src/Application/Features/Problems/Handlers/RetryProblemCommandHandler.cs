using Application.Common.Exceptions;
using Application.Common.Interfaces;
using Application.DTOs;
using Application.Features.Problems.Commands;
using Domain.Entities;
using Microsoft.Extensions.Logging;

namespace Application.Features.Problems.Handlers;

public class RetryProblemCommandHandler : ICommandHandler<RetryProblemCommand, ProblemResult>
{
    private readonly IProblemRepository _problemRepository;
    private readonly IMLService _mlService;
    private readonly IUnitOfWork _unitOfWork;
    private readonly ILogger<RetryProblemCommandHandler> _logger;

    public RetryProblemCommandHandler(
        IProblemRepository problemRepository,
        IMLService mlService,
        IUnitOfWork unitOfWork,
        ILogger<RetryProblemCommandHandler> logger)
    {
        _problemRepository = problemRepository;
        _mlService = mlService;
        _unitOfWork = unitOfWork;
        _logger = logger;
    }

    public async Task<ProblemResult> Handle(RetryProblemCommand request, CancellationToken cancellationToken)
    {
        var problem = await _problemRepository.GetByIdAsync(request.ProblemId, cancellationToken);

        if (problem == null)
        {
            _logger.LogWarning("Problem {ProblemId} not found", request.ProblemId);
            throw new NotFoundException($"Problem with ID {request.ProblemId} not found");
        }

        // Verify ownership
        if (problem.UserId != request.UserId)
        {
            _logger.LogWarning("User {UserId} attempted to retry problem {ProblemId} owned by {OwnerId}",
                request.UserId, request.ProblemId, problem.UserId);
            throw new UnauthorizedException("You are not authorized to retry this problem");
        }

        try
        {
            // Mark as processing
            problem.MarkAsProcessing();
            await _unitOfWork.SaveChangesAsync(cancellationToken);

            _logger.LogInformation("Retrying problem {ProblemId}", problem.Id);

            // Retry solving
            var solution = await _mlService.SolveProblemAsync(problem, cancellationToken);

            if (solution != null)
            {
                problem.MarkAsCompleted(solution);
                _logger.LogInformation("Problem {ProblemId} solved successfully on retry", problem.Id);
            }
            else
            {
                problem.MarkAsFailed("Failed to generate solution on retry");
                _logger.LogWarning("Failed to solve problem {ProblemId} on retry", problem.Id);
            }

            await _unitOfWork.SaveChangesAsync(cancellationToken);

            // Reload problem with solution
            var problemWithSolution = await _problemRepository.GetByIdWithSolutionAsync(problem.Id, cancellationToken);

            return new ProblemResult
            {
                Success = solution != null,
                Message = solution != null ? "Problem solved successfully" : "Failed to solve problem",
                Problem = MapToDto(problemWithSolution!)
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrying problem {ProblemId}", request.ProblemId);
            problem.MarkAsFailed($"Error during retry: {ex.Message}");
            await _unitOfWork.SaveChangesAsync(cancellationToken);

            return new ProblemResult
            {
                Success = false,
                Message = $"Failed to retry problem: {ex.Message}"
            };
        }
    }

    private static ProblemDto MapToDto(Problem problem)
    {
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
