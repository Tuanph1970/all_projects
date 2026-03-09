using MediatR;
using ProblemService.Application.Common.Exceptions;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Domain.Entities;

namespace ProblemService.Application.Features.Problems.Commands;

public record UpdateProblemStatusCommand(Guid ProblemId, ProblemStatus Status, string? ExtractedText = null) : IRequest;

public class UpdateProblemStatusCommandHandler : IRequestHandler<UpdateProblemStatusCommand>
{
    private readonly IUnitOfWork _uow;

    public UpdateProblemStatusCommandHandler(IUnitOfWork uow) => _uow = uow;

    public async Task Handle(UpdateProblemStatusCommand request, CancellationToken cancellationToken)
    {
        var problem = await _uow.Problems.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.ProblemId);

        problem.UpdateStatus(request.Status, request.ExtractedText);
        await _uow.SaveChangesAsync(cancellationToken);
    }
}
