using AuthService.Application.Common.Exceptions;
using AuthService.Application.Common.Interfaces;
using AuthService.Application.Features.Authentication.Commands;
using AuthService.Domain.Entities;
using FluentAssertions;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;

namespace AuthService.Tests.Application.Commands;

public class RefreshTokenCommandHandlerTests
{
    private readonly Mock<IUnitOfWork> _mockUow = new();
    private readonly Mock<IUserRepository> _mockUserRepo = new();
    private readonly Mock<IJwtTokenGenerator> _mockJwt = new();
    private readonly Mock<ICacheService> _mockCache = new();
    private readonly IConfiguration _config;
    private readonly ILogger<RefreshTokenCommandHandler> _logger;
    private readonly RefreshTokenCommandHandler _handler;

    private static readonly Guid _userId = Guid.NewGuid();
    private const string OldRefreshToken = "old_refresh_token";
    private const string NewRefreshToken = "new_refresh_token";
    private const string NewAccessToken = "new_access_token";

    public RefreshTokenCommandHandlerTests()
    {
        _config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Jwt:RefreshTokenExpirationDays"] = "7"
            })
            .Build();

        _logger = Mock.Of<ILogger<RefreshTokenCommandHandler>>();
        _mockUow.Setup(u => u.Users).Returns(_mockUserRepo.Object);

        _handler = new RefreshTokenCommandHandler(
            _mockUow.Object,
            _mockJwt.Object,
            _mockCache.Object,
            _config,
            _logger);
    }

    private void SetupValidRefreshFlow()
    {
        var entry = new RefreshTokenEntry(_userId, DateTime.UtcNow.AddDays(7));
        _mockCache.Setup(c => c.GetAsync<RefreshTokenEntry>(
            It.Is<string>(k => k.Contains(OldRefreshToken)), It.IsAny<CancellationToken>()))
            .ReturnsAsync(entry);

        var user = User.Create("user", "user@test.com", "hash");
        _mockUserRepo.Setup(r => r.GetByIdAsync(_userId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);

        _mockCache.Setup(c => c.RemoveAsync(
            It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        _mockJwt.Setup(j => j.GenerateAccessToken(It.IsAny<User>())).Returns(NewAccessToken);
        _mockJwt.Setup(j => j.GenerateRefreshToken()).Returns(NewRefreshToken);

        _mockCache.Setup(c => c.SetAsync(
            It.IsAny<string>(), It.IsAny<RefreshTokenEntry>(),
            It.IsAny<DistributedCacheEntryOptions?>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
    }

    [Fact]
    public async Task Handle_ValidRefreshToken_ReturnsNewTokenPair()
    {
        SetupValidRefreshFlow();

        var result = await _handler.Handle(new RefreshTokenCommand(OldRefreshToken), CancellationToken.None);

        result.Should().NotBeNull();
        result.AccessToken.Should().Be(NewAccessToken);
        result.RefreshToken.Should().Be(NewRefreshToken);
    }

    [Fact]
    public async Task Handle_TokenNotInCache_ThrowsUnauthorizedException()
    {
        _mockCache.Setup(c => c.GetAsync<RefreshTokenEntry>(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((RefreshTokenEntry?)null);

        var act = async () => await _handler.Handle(new RefreshTokenCommand("bad_token"), CancellationToken.None);

        await act.Should().ThrowAsync<UnauthorizedException>();
    }

    [Fact]
    public async Task Handle_ExpiredRefreshToken_ThrowsUnauthorizedException()
    {
        var expiredEntry = new RefreshTokenEntry(_userId, DateTime.UtcNow.AddDays(-1)); // expired
        _mockCache.Setup(c => c.GetAsync<RefreshTokenEntry>(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(expiredEntry);
        _mockCache.Setup(c => c.RemoveAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var act = async () => await _handler.Handle(new RefreshTokenCommand(OldRefreshToken), CancellationToken.None);

        await act.Should().ThrowAsync<UnauthorizedException>();
    }

    [Fact]
    public async Task Handle_UserNotFound_ThrowsUnauthorizedException()
    {
        var entry = new RefreshTokenEntry(Guid.NewGuid(), DateTime.UtcNow.AddDays(7));
        _mockCache.Setup(c => c.GetAsync<RefreshTokenEntry>(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(entry);
        _mockCache.Setup(c => c.RemoveAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        _mockUserRepo.Setup(r => r.GetByIdAsync(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((User?)null);

        var act = async () => await _handler.Handle(new RefreshTokenCommand(OldRefreshToken), CancellationToken.None);

        await act.Should().ThrowAsync<UnauthorizedException>();
    }

    [Fact]
    public async Task Handle_InactiveUser_ThrowsUnauthorizedException()
    {
        var entry = new RefreshTokenEntry(_userId, DateTime.UtcNow.AddDays(7));
        _mockCache.Setup(c => c.GetAsync<RefreshTokenEntry>(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(entry);
        _mockCache.Setup(c => c.RemoveAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var inactiveUser = User.Create("user", "user@test.com", "hash");
        inactiveUser.Deactivate();
        _mockUserRepo.Setup(r => r.GetByIdAsync(_userId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(inactiveUser);

        var act = async () => await _handler.Handle(new RefreshTokenCommand(OldRefreshToken), CancellationToken.None);

        await act.Should().ThrowAsync<UnauthorizedException>();
    }

    [Fact]
    public async Task Handle_ValidRefresh_RemovesOldTokenFromCache()
    {
        SetupValidRefreshFlow();

        await _handler.Handle(new RefreshTokenCommand(OldRefreshToken), CancellationToken.None);

        _mockCache.Verify(c => c.RemoveAsync(
            It.Is<string>(k => k.Contains(OldRefreshToken)), It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task Handle_ValidRefresh_StoresNewTokenInCache()
    {
        SetupValidRefreshFlow();

        await _handler.Handle(new RefreshTokenCommand(OldRefreshToken), CancellationToken.None);

        _mockCache.Verify(c => c.SetAsync(
            It.Is<string>(k => k.Contains(NewRefreshToken)),
            It.IsAny<RefreshTokenEntry>(),
            It.IsAny<DistributedCacheEntryOptions?>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }
}
