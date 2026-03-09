using MediatR;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using AuthService.Application.Common.Exceptions;
using AuthService.Application.Common.Interfaces;
using AuthService.Application.DTOs;

namespace AuthService.Application.Features.Authentication.Commands;

public record RefreshTokenCommand(string RefreshToken) : IRequest<AuthResultDto>;

public sealed class RefreshTokenCommandHandler : IRequestHandler<RefreshTokenCommand, AuthResultDto>
{
    private readonly IUnitOfWork _uow;
    private readonly IJwtTokenGenerator _jwt;
    private readonly ICacheService _cache;
    private readonly IConfiguration _config;
    private readonly ILogger<RefreshTokenCommandHandler> _logger;

    private int RefreshTokenDays =>
        int.TryParse(_config["Jwt:RefreshTokenExpirationDays"], out var d) ? d : 7;

    public RefreshTokenCommandHandler(
        IUnitOfWork uow, IJwtTokenGenerator jwt, ICacheService cache,
        IConfiguration config, ILogger<RefreshTokenCommandHandler> logger)
    {
        _uow = uow; _jwt = jwt; _cache = cache; _config = config; _logger = logger;
    }

    public async Task<AuthResultDto> Handle(RefreshTokenCommand request, CancellationToken ct)
    {
        var entry = await _cache.GetAsync<RefreshTokenEntry>(CacheKeys.RefreshToken(request.RefreshToken), ct);
        if (entry is null || entry.ExpiresAt < DateTime.UtcNow)
        {
            await _cache.RemoveAsync(CacheKeys.RefreshToken(request.RefreshToken), ct);
            throw new UnauthorizedException("Refresh token is invalid or has expired.");
        }

        var user = await _uow.Users.GetByIdAsync(entry.UserId, ct);
        if (user is null || !user.IsActive)
        {
            await _cache.RemoveAsync(CacheKeys.RefreshToken(request.RefreshToken), ct);
            throw new UnauthorizedException("User not found or account deactivated.");
        }

        await _cache.RemoveAsync(CacheKeys.RefreshToken(request.RefreshToken), ct);

        var newAccess  = _jwt.GenerateAccessToken(user);
        var newRefresh = _jwt.GenerateRefreshToken();
        var expiresAt  = DateTime.UtcNow.AddHours(1);

        await _cache.SetAsync(
            CacheKeys.RefreshToken(newRefresh),
            new RefreshTokenEntry(user.Id, DateTime.UtcNow.AddDays(RefreshTokenDays)),
            new DistributedCacheEntryOptions { AbsoluteExpirationRelativeToNow = TimeSpan.FromDays(RefreshTokenDays) },
            ct);

        _logger.LogInformation("Tokens refreshed for user {UserId}", user.Id);
        return new AuthResultDto(user.Id, user.Username, user.Email, user.FullName, user.Role, newAccess, newRefresh, expiresAt);
    }
}
