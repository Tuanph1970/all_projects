using MediatR;
using ProblemService.Application.Common.Exceptions;
using ProblemService.Application.Common.Interfaces;

namespace ProblemService.Application.Features.Problems.Commands;

public record DeleteProblemCommand(Guid ProblemId, Guid UserId) : IRequest;

public class DeleteProblemCommandHandler : IRequestHandler<DeleteProblemCommand>
{
    private readonly IUnitOfWork _uow;

    public DeleteProblemCommandHandler(IUnitOfWork uow) => _uow = uow;

    public async Task Handle(DeleteProblemCommand request, CancellationToken cancellationToken)
    {
        var problem = await _uow.Problems.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Domain.Entities.Problem), request.ProblemId);

        if (problem.UserId != request.UserId)
            throw new UnauthorizedException("You are not authorized to delete this problem.");

        _uow.Problems.Remove(problem);
        await _uow.SaveChangesAsync(cancellationToken);
    }
}
