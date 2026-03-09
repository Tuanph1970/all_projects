using FluentValidation;
using MediatR;
using ProblemService.Application.Common.Exceptions;
using ProblemService.Application.Common.Interfaces;

namespace ProblemService.Application.Features.Problems.Commands;

public record UpdateProblemCommand(
    Guid ProblemId,
    Guid UserId,
    string? Title,
    string? Description,
    string? Category,
    string? Difficulty
) : IRequest;

public class UpdateProblemCommandValidator : AbstractValidator<UpdateProblemCommand>
{
    public UpdateProblemCommandValidator()
    {
        RuleFor(x => x.ProblemId).NotEmpty();
        RuleFor(x => x.UserId).NotEmpty();
        RuleFor(x => x.Title).MaximumLength(200).When(x => x.Title != null);
    }
}

public class UpdateProblemCommandHandler : IRequestHandler<UpdateProblemCommand>
{
    private readonly IUnitOfWork _uow;

    public UpdateProblemCommandHandler(IUnitOfWork uow) => _uow = uow;

    public async Task Handle(UpdateProblemCommand request, CancellationToken cancellationToken)
    {
        var problem = await _uow.Problems.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Domain.Entities.Problem), request.ProblemId);

        if (problem.UserId != request.UserId)
            throw new UnauthorizedException("You are not authorized to update this problem.");

        problem.Update(request.Title, request.Description, request.Category, request.Difficulty);
        await _uow.SaveChangesAsync(cancellationToken);
    }
}
