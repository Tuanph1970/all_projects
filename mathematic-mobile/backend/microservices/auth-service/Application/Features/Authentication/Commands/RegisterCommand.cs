using FluentValidation;
using FluentValidation.Results;
using MediatR;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using AuthService.Application.Common.Exceptions;
using AuthService.Application.Common.Interfaces;
using AuthService.Application.DTOs;
using AuthService.Domain.Entities;

namespace AuthService.Application.Features.Authentication.Commands;

public record RegisterCommand(string Username, string Email, string Password, string? FullName) : IRequest<AuthResultDto>;

public class RegisterCommandValidator : AbstractValidator<RegisterCommand>
{
    public RegisterCommandValidator()
    {
        RuleFor(x => x.Username).NotEmpty().Length(3, 50);
        RuleFor(x => x.Email).NotEmpty().EmailAddress();
        RuleFor(x => x.Password).NotEmpty().MinimumLength(6).MaximumLength(100);
    }
}

public sealed class RegisterCommandHandler : IRequestHandler<RegisterCommand, AuthResultDto>
{
    private readonly IUnitOfWork _uow;
    private readonly IPasswordHasher _hasher;
    private readonly IJwtTokenGenerator _jwt;
    private readonly ICacheService _cache;
    private readonly IConfiguration _config;
    private readonly ILogger<RegisterCommandHandler> _logger;

    private int RefreshTokenDays =>
        int.TryParse(_config["Jwt:RefreshTokenExpirationDays"], out var d) ? d : 7;

    public RegisterCommandHandler(
        IUnitOfWork uow, IPasswordHasher hasher, IJwtTokenGenerator jwt,
        ICacheService cache, IConfiguration config, ILogger<RegisterCommandHandler> logger)
    {
        _uow = uow; _hasher = hasher; _jwt = jwt;
        _cache = cache; _config = config; _logger = logger;
    }

    public async Task<AuthResultDto> Handle(RegisterCommand request, CancellationToken ct)
    {
        if (await _uow.Users.ExistsByUsernameAsync(request.Username, ct))
            throw new AppValidationException([new ValidationFailure("Username", "Username already exists.")]);
        if (await _uow.Users.ExistsByEmailAsync(request.Email, ct))
            throw new AppValidationException([new ValidationFailure("Email", "Email already exists.")]);

        var user = User.Create(request.Username, request.Email, _hasher.Hash(request.Password), request.FullName);
        await _uow.Users.AddAsync(user, ct);
        await _uow.SaveChangesAsync(ct);

        var accessToken  = _jwt.GenerateAccessToken(user);
        var refreshToken = _jwt.GenerateRefreshToken();
        var expiresAt    = DateTime.UtcNow.AddHours(1);

        await _cache.SetAsync(
            CacheKeys.RefreshToken(refreshToken),
            new RefreshTokenEntry(user.Id, DateTime.UtcNow.AddDays(RefreshTokenDays)),
            new DistributedCacheEntryOptions { AbsoluteExpirationRelativeToNow = TimeSpan.FromDays(RefreshTokenDays) },
            ct);

        _logger.LogInformation("User {UserId} registered", user.Id);
        return new AuthResultDto(user.Id, user.Username, user.Email, user.FullName, user.Role, accessToken, refreshToken, expiresAt);
    }
}
