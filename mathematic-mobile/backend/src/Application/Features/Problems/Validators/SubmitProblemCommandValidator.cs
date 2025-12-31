using Application.Features.Problems.Commands;
using FluentValidation;

namespace Application.Features.Problems.Validators;

public class SubmitProblemCommandValidator : AbstractValidator<SubmitProblemCommand>
{
    private static readonly string[] AllowedExtensions = { ".jpg", ".jpeg", ".png", ".bmp" };
    private const long MaxFileSize = 10 * 1024 * 1024; // 10MB

    public SubmitProblemCommandValidator()
    {
        RuleFor(x => x.UserId)
            .NotEmpty()
            .WithMessage("User ID is required");

        RuleFor(x => x.ImageFile)
            .NotNull()
            .WithMessage("Image file is required")
            .Must(file => file != null && file.Length > 0)
            .WithMessage("Image file cannot be empty")
            .Must(file => file == null || file.Length <= MaxFileSize)
            .WithMessage($"Image file size must not exceed {MaxFileSize / 1024 / 1024}MB")
            .Must(file =>
            {
                if (file == null) return true;
                var extension = Path.GetExtension(file.FileName).ToLowerInvariant();
                return AllowedExtensions.Contains(extension);
            })
            .WithMessage($"Only image files are allowed: {string.Join(", ", AllowedExtensions)}");

        RuleFor(x => x.Category)
            .NotEmpty()
            .WithMessage("Category is required")
            .MaximumLength(50)
            .WithMessage("Category must not exceed 50 characters");

        RuleFor(x => x.Description)
            .MaximumLength(500)
            .WithMessage("Description must not exceed 500 characters")
            .When(x => !string.IsNullOrEmpty(x.Description));
    }
}
