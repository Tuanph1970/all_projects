using FluentValidation.Results;
using MediatR;
using AuthService.Application.Common.Exceptions;
using AuthService.Application.Common.Interfaces;
using AuthService.Domain.Entities;

namespace AuthService.Application.Features.Authentication.Commands;

public record UpdateProfileCommand(Guid UserId, string? FullName, string? Email) : IRequest;

public sealed class UpdateProfileCommandHandler : IRequestHandler<UpdateProfileCommand>
{
    private readonly IUnitOfWork _uow;

    public UpdateProfileCommandHandler(IUnitOfWork uow) => _uow = uow;

    public async Task Handle(UpdateProfileCommand request, CancellationToken ct)
    {
        var user = await _uow.Users.GetByIdAsync(request.UserId, ct)
            ?? throw new NotFoundException(nameof(User), request.UserId);

        if (request.Email is not null && request.Email != user.Email &&
            await _uow.Users.ExistsByEmailAsync(request.Email, ct))
            throw new AppValidationException([new ValidationFailure("Email", "Email already in use.")]);

        user.UpdateProfile(request.FullName, request.Email);
        await _uow.SaveChangesAsync(ct);
    }
}
