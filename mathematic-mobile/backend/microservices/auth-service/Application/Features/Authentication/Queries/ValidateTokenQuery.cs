using MediatR;
using AuthService.Application.Common.Interfaces;
using AuthService.Application.DTOs;

namespace AuthService.Application.Features.Authentication.Queries;

public record ValidateTokenQuery(string Token) : IRequest<TokenValidationDto>;

public record TokenValidationDto(bool IsValid, Guid? UserId, string? Username, string? Role, string? Message);

public sealed class ValidateTokenQueryHandler : IRequestHandler<ValidateTokenQuery, TokenValidationDto>
{
    private readonly IUnitOfWork _uow;
    private readonly IJwtTokenGenerator _jwt;

    public ValidateTokenQueryHandler(IUnitOfWork uow, IJwtTokenGenerator jwt)
    { _uow = uow; _jwt = jwt; }

    public async Task<TokenValidationDto> Handle(ValidateTokenQuery request, CancellationToken ct)
    {
        var userId = _jwt.GetUserIdFromToken(request.Token);
        if (userId is null) return new(false, null, null, null, "Invalid or expired token.");

        var user = await _uow.Users.GetByIdAsync(userId.Value, ct);
        if (user is null || !user.IsActive)
            return new(false, null, null, null, "User not found or inactive.");

        return new(true, user.Id, user.Username, user.Role, "Token is valid.");
    }
}
