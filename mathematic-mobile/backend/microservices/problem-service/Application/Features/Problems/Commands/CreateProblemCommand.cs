using FluentValidation;
using MediatR;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Application.Features.Problems.DTOs;
using ProblemService.Application.Features.Problems.Extensions;
using ProblemService.Domain.Entities;

namespace ProblemService.Application.Features.Problems.Commands;

public record CreateProblemCommand(
    Guid UserId,
    string Title,
    string? Description,
    string? Category,
    string? Difficulty
) : IRequest<ProblemDto>;

public class CreateProblemCommandValidator : AbstractValidator<CreateProblemCommand>
{
    public CreateProblemCommandValidator()
    {
        RuleFor(x => x.UserId).NotEmpty();
        RuleFor(x => x.Title).NotEmpty().MaximumLength(200);
    }
}

public class CreateProblemCommandHandler : IRequestHandler<CreateProblemCommand, ProblemDto>
{
    private readonly IUnitOfWork _uow;

    public CreateProblemCommandHandler(IUnitOfWork uow) => _uow = uow;

    public async Task<ProblemDto> Handle(CreateProblemCommand request, CancellationToken cancellationToken)
    {
        var problem = Problem.Create(request.UserId, request.Title, request.Description, request.Category, request.Difficulty);
        _uow.Problems.Add(problem);
        await _uow.SaveChangesAsync(cancellationToken);

        _uow.ProblemHistories.Add(ProblemHistory.Create(problem.Id, request.UserId, "Created", $"Problem created: {request.Title}"));
        await _uow.SaveChangesAsync(cancellationToken);

        return problem.ToDto();
    }
}
