using Application.Common.Exceptions;
using Application.Common.Interfaces;
using Application.Features.Problems.Commands;
using Microsoft.Extensions.Logging;

namespace Application.Features.Problems.Handlers;

public class DeleteProblemCommandHandler : ICommandHandler<DeleteProblemCommand, bool>
{
    private readonly IProblemRepository _problemRepository;
    private readonly IFileStorageService _fileStorageService;
    private readonly IUnitOfWork _unitOfWork;
    private readonly ILogger<DeleteProblemCommandHandler> _logger;

    public DeleteProblemCommandHandler(
        IProblemRepository problemRepository,
        IFileStorageService fileStorageService,
        IUnitOfWork unitOfWork,
        ILogger<DeleteProblemCommandHandler> logger)
    {
        _problemRepository = problemRepository;
        _fileStorageService = fileStorageService;
        _unitOfWork = unitOfWork;
        _logger = logger;
    }

    public async Task<bool> Handle(DeleteProblemCommand request, CancellationToken cancellationToken)
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
            _logger.LogWarning("User {UserId} attempted to delete problem {ProblemId} owned by {OwnerId}",
                request.UserId, request.ProblemId, problem.UserId);
            throw new UnauthorizedException("You are not authorized to delete this problem");
        }

        // Delete image from storage
        await _fileStorageService.DeleteImageAsync(problem.ImageUrl, cancellationToken);

        // Delete problem from database
        await _problemRepository.DeleteAsync(problem, cancellationToken);
        await _unitOfWork.SaveChangesAsync(cancellationToken);

        _logger.LogInformation("Problem {ProblemId} deleted successfully by user {UserId}",
            request.ProblemId, request.UserId);

        return true;
    }
}
