using Application.Common.Interfaces;
using Application.DTOs;
using Application.Features.Problems.Commands;
using Domain.Entities;
using Microsoft.Extensions.Logging;

namespace Application.Features.Problems.Handlers;

public class SubmitProblemCommandHandler : ICommandHandler<SubmitProblemCommand, ProblemResult>
{
    private readonly IProblemRepository _problemRepository;
    private readonly IFileStorageService _fileStorageService;
    private readonly IMLService _mlService;
    private readonly IUnitOfWork _unitOfWork;
    private readonly ILogger<SubmitProblemCommandHandler> _logger;

    public SubmitProblemCommandHandler(
        IProblemRepository problemRepository,
        IFileStorageService fileStorageService,
        IMLService mlService,
        IUnitOfWork unitOfWork,
        ILogger<SubmitProblemCommandHandler> logger)
    {
        _problemRepository = problemRepository;
        _fileStorageService = fileStorageService;
        _mlService = mlService;
        _unitOfWork = unitOfWork;
        _logger = logger;
    }

    public async Task<ProblemResult> Handle(SubmitProblemCommand request, CancellationToken cancellationToken)
    {
        try
        {
            // Upload image to storage
            _logger.LogInformation("Uploading image for user {UserId}", request.UserId);
            var imageUrl = await _fileStorageService.UploadImageAsync(request.ImageFile, cancellationToken);

            // Create problem entity
            var problem = new Problem(
                userId: request.UserId,
                imageUrl: imageUrl,
                category: request.Category,
                description: request.Description
            );

            // Save problem to database
            await _problemRepository.AddAsync(problem, cancellationToken);
            await _unitOfWork.SaveChangesAsync(cancellationToken);

            _logger.LogInformation("Problem {ProblemId} created successfully for user {UserId}", problem.Id, request.UserId);

            // Mark as processing
            problem.MarkAsProcessing();
            await _unitOfWork.SaveChangesAsync(cancellationToken);

            // Solve problem asynchronously (fire and forget in real scenario, but here we await)
            _logger.LogInformation("Sending problem {ProblemId} to ML service", problem.Id);
            var solution = await _mlService.SolveProblemAsync(problem, cancellationToken);

            if (solution != null)
            {
                problem.MarkAsCompleted(solution);
                _logger.LogInformation("Problem {ProblemId} solved successfully", problem.Id);
            }
            else
            {
                problem.MarkAsFailed("Failed to generate solution");
                _logger.LogWarning("Failed to solve problem {ProblemId}", problem.Id);
            }

            await _unitOfWork.SaveChangesAsync(cancellationToken);

            // Reload problem with solution
            var problemWithSolution = await _problemRepository.GetByIdWithSolutionAsync(problem.Id, cancellationToken);

            return new ProblemResult
            {
                Success = true,
                Message = "Problem submitted successfully",
                Problem = MapToDto(problemWithSolution!)
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error submitting problem for user {UserId}", request.UserId);
            return new ProblemResult
            {
                Success = false,
                Message = $"Failed to submit problem: {ex.Message}"
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
