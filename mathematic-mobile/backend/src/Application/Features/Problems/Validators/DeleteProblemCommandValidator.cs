using Application.Features.Problems.Commands;
using FluentValidation;

namespace Application.Features.Problems.Validators;

public class DeleteProblemCommandValidator : AbstractValidator<DeleteProblemCommand>
{
    public DeleteProblemCommandValidator()
    {
        RuleFor(x => x.ProblemId)
            .NotEmpty()
            .WithMessage("Problem ID is required");

        RuleFor(x => x.UserId)
            .NotEmpty()
            .WithMessage("User ID is required");
    }
}
