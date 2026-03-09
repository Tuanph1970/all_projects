using MediatR;
using ProblemService.Application.Common.Exceptions;
using ProblemService.Application.Common.Interfaces;

namespace ProblemService.Application.Features.Problems.Commands;

public record SendToSolutionServiceCommand(Guid ProblemId, Guid UserId) : IRequest;

public class SendToSolutionServiceCommandHandler : IRequestHandler<SendToSolutionServiceCommand>
{
    private readonly IUnitOfWork _uow;
    private readonly ISolutionServiceClient _solutionClient;
    private readonly ILogger<SendToSolutionServiceCommandHandler> _logger;

    public SendToSolutionServiceCommandHandler(IUnitOfWork uow, ISolutionServiceClient solutionClient, ILogger<SendToSolutionServiceCommandHandler> logger)
    {
        _uow = uow;
        _solutionClient = solutionClient;
        _logger = logger;
    }

    public async Task Handle(SendToSolutionServiceCommand request, CancellationToken cancellationToken)
    {
        var problem = await _uow.Problems.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Domain.Entities.Problem), request.ProblemId);

        if (problem.UserId != request.UserId)
            throw new UnauthorizedException("You are not authorized to process this problem.");

        if (string.IsNullOrEmpty(problem.ImagePath))
            throw new InvalidOperationException("No image uploaded for this problem.");

        problem.SetProcessing();
        await _uow.SaveChangesAsync(cancellationToken);

        var req = new ProcessImageRequest(problem.Id, problem.ImagePath, request.UserId);
        var response = await _solutionClient.ProcessImageAsync(req, cancellationToken);

        if (response?.Success == true)
        {
            _logger.LogInformation("Problem {ProblemId} sent to Solution Service successfully", request.ProblemId);
        }
        else
        {
            _logger.LogWarning("Solution Service returned failure for problem {ProblemId}: {Message}", request.ProblemId, response?.Message ?? "Unknown error");
            problem.RevertToPending();
            await _uow.SaveChangesAsync(cancellationToken);
            throw new InvalidOperationException(response?.Message ?? "Failed to process problem");
        }
    }
}
