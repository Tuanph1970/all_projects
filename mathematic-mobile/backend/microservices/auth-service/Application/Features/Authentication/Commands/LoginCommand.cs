using FluentValidation;
using MediatR;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using AuthService.Application.Common.Exceptions;
using AuthService.Application.Common.Interfaces;
using AuthService.Application.DTOs;

namespace AuthService.Application.Features.Authentication.Commands;

// Command
public record LoginCommand(string UsernameOrEmail, string Password) : IRequest<AuthResultDto>;

// Validator
public class LoginCommandValidator : AbstractValidator<LoginCommand>
{
    public LoginCommandValidator()
    {
        RuleFor(x => x.UsernameOrEmail).NotEmpty();
        RuleFor(x => x.Password).NotEmpty().MinimumLength(6);
    }
}

// Handler
public sealed class LoginCommandHandler : IRequestHandler<LoginCommand, AuthResultDto>
{
    private readonly IUnitOfWork _uow;
    private readonly IPasswordHasher _hasher;
    private readonly IJwtTokenGenerator _jwt;
    private readonly ICacheService _cache;
    private readonly IConfiguration _config;
    private readonly ILogger<LoginCommandHandler> _logger;

    private int RefreshTokenDays =>
        int.TryParse(_config["Jwt:RefreshTokenExpirationDays"], out var d) ? d : 7;

    public LoginCommandHandler(
        IUnitOfWork uow,
        IPasswordHasher hasher,
        IJwtTokenGenerator jwt,
        ICacheService cache,
        IConfiguration config,
        ILogger<LoginCommandHandler> logger)
    {
        _uow = uow; _hasher = hasher; _jwt = jwt;
        _cache = cache; _config = config; _logger = logger;
    }

    public async Task<AuthResultDto> Handle(LoginCommand request, CancellationToken ct)
    {
        var user = await _uow.Users.GetByUsernameOrEmailAsync(request.UsernameOrEmail, ct);
        if (user is null || !_hasher.Verify(request.Password, user.PasswordHash))
            throw new UnauthorizedException("Invalid username or password.");

        if (!user.IsActive) throw new UnauthorizedException("Account is deactivated.");

        user.RecordLogin();
        await _uow.SaveChangesAsync(ct);

        var accessToken  = _jwt.GenerateAccessToken(user);
        var refreshToken = _jwt.GenerateRefreshToken();
        var expiresAt    = DateTime.UtcNow.AddHours(1);

        await _cache.SetAsync(
            CacheKeys.RefreshToken(refreshToken),
            new RefreshTokenEntry(user.Id, DateTime.UtcNow.AddDays(RefreshTokenDays)),
            new DistributedCacheEntryOptions { AbsoluteExpirationRelativeToNow = TimeSpan.FromDays(RefreshTokenDays) },
            ct);

        _logger.LogInformation("User {UserId} logged in", user.Id);
        return new AuthResultDto(user.Id, user.Username, user.Email, user.FullName, user.Role, accessToken, refreshToken, expiresAt);
    }
}

// Shared token entry record used across commands
public record RefreshTokenEntry(Guid UserId, DateTime ExpiresAt);
