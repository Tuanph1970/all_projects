using FluentValidation;
using MediatR;
using Microsoft.AspNetCore.Http;
using ProblemService.Application.Common.Exceptions;
using ProblemService.Application.Common.Interfaces;

namespace ProblemService.Application.Features.Problems.Commands;

public record UploadImageCommand(Guid ProblemId, Guid UserId, IFormFile File, string UploadPath) : IRequest<string>;

public class UploadImageCommandValidator : AbstractValidator<UploadImageCommand>
{
    private static readonly string[] AllowedExtensions = [".jpg", ".jpeg", ".png", ".bmp"];
    private const long MaxFileSize = 10 * 1024 * 1024; // 10MB

    public UploadImageCommandValidator()
    {
        RuleFor(x => x.File)
            .NotNull()
            .Must(f => f.Length > 0).WithMessage("File cannot be empty.")
            .Must(f => f.Length <= MaxFileSize).WithMessage("File size exceeds 10MB limit.")
            .Must(f => AllowedExtensions.Contains(Path.GetExtension(f.FileName).ToLowerInvariant()))
            .WithMessage("Invalid file type. Allowed: jpg, jpeg, png, bmp.");
    }
}

public class UploadImageCommandHandler : IRequestHandler<UploadImageCommand, string>
{
    private readonly IUnitOfWork _uow;

    public UploadImageCommandHandler(IUnitOfWork uow) => _uow = uow;

    public async Task<string> Handle(UploadImageCommand request, CancellationToken cancellationToken)
    {
        var problem = await _uow.Problems.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Domain.Entities.Problem), request.ProblemId);

        if (problem.UserId != request.UserId)
            throw new UnauthorizedException("You are not authorized to upload an image for this problem.");

        Directory.CreateDirectory(request.UploadPath);
        var extension = Path.GetExtension(request.File.FileName).ToLowerInvariant();
        var fileName = $"{request.ProblemId}_{Guid.NewGuid()}{extension}";
        var filePath = Path.Combine(request.UploadPath, fileName);

        await using (var stream = new FileStream(filePath, FileMode.Create))
            await request.File.CopyToAsync(stream, cancellationToken);

        problem.SetImage(fileName);
        await _uow.SaveChangesAsync(cancellationToken);

        return fileName;
    }
}
