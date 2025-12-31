using Application.Features.Problems.Commands;
using FluentValidation;

namespace Application.Features.Problems.Validators;

public class RetryProblemCommandValidator : AbstractValidator<RetryProblemCommand>
{
    public RetryProblemCommandValidator()
    {
        RuleFor(x => x.ProblemId)
            .NotEmpty()
            .WithMessage("Problem ID is required");

        RuleFor(x => x.UserId)
            .NotEmpty()
            .WithMessage("User ID is required");
    }
}
