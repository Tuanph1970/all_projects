using AuthService.Application.Common.Exceptions;
using AuthService.Application.Common.Interfaces;
using AuthService.Application.DTOs;
using AuthService.Application.Features.Authentication.Commands;
using AuthService.Domain.Entities;
using FluentAssertions;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;

namespace AuthService.Tests.Application.Commands;

public class RegisterCommandHandlerTests
{
    private readonly Mock<IUnitOfWork> _mockUow = new();
    private readonly Mock<IUserRepository> _mockUserRepo = new();
    private readonly Mock<IPasswordHasher> _mockHasher = new();
    private readonly Mock<IJwtTokenGenerator> _mockJwt = new();
    private readonly Mock<ICacheService> _mockCache = new();
    private readonly IConfiguration _config;
    private readonly ILogger<RegisterCommandHandler> _logger;
    private readonly RegisterCommandHandler _handler;

    public RegisterCommandHandlerTests()
    {
        // Config with refresh token expiration
        _config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Jwt:RefreshTokenExpirationDays"] = "7"
            })
            .Build();

        _logger = Mock.Of<ILogger<RegisterCommandHandler>>();

        _mockUow.Setup(u => u.Users).Returns(_mockUserRepo.Object);

        _handler = new RegisterCommandHandler(
            _mockUow.Object,
            _mockHasher.Object,
            _mockJwt.Object,
            _mockCache.Object,
            _config,
            _logger);
    }

    private void SetupHappyPath(string username = "testuser", string email = "test@example.com")
    {
        _mockUserRepo.Setup(r => r.ExistsByUsernameAsync(username, It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);
        _mockUserRepo.Setup(r => r.ExistsByEmailAsync(email, It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        _mockHasher.Setup(h => h.Hash(It.IsAny<string>())).Returns("hashed_password");

        _mockUserRepo.Setup(r => r.AddAsync(It.IsAny<User>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        _mockUow.Setup(u => u.SaveChangesAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(1);

        _mockJwt.Setup(j => j.GenerateAccessToken(It.IsAny<User>())).Returns("access_token_xyz");
        _mockJwt.Setup(j => j.GenerateRefreshToken()).Returns("refresh_token_xyz");

        _mockCache.Setup(c => c.SetAsync(
            It.IsAny<string>(), It.IsAny<RefreshTokenEntry>(),
            It.IsAny<DistributedCacheEntryOptions?>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
    }

    [Fact]
    public async Task Handle_ValidCommand_ReturnsAuthResultDtoWithTokens()
    {
        SetupHappyPath();
        var cmd = new RegisterCommand("testuser", "test@example.com", "pass123", "Test User");

        var result = await _handler.Handle(cmd, CancellationToken.None);

        result.Should().NotBeNull();
        result.AccessToken.Should().Be("access_token_xyz");
        result.RefreshToken.Should().Be("refresh_token_xyz");
        result.Username.Should().Be("testuser");
        result.Email.Should().Be("test@example.com");
    }

    [Fact]
    public async Task Handle_ValidCommand_HashesPassword()
    {
        SetupHappyPath();
        var cmd = new RegisterCommand("testuser", "test@example.com", "my_plain_password", null);

        await _handler.Handle(cmd, CancellationToken.None);

        _mockHasher.Verify(h => h.Hash("my_plain_password"), Times.Once);
    }

    [Fact]
    public async Task Handle_ValidCommand_AddsUserToRepository()
    {
        SetupHappyPath();
        var cmd = new RegisterCommand("testuser", "test@example.com", "pass123", null);

        await _handler.Handle(cmd, CancellationToken.None);

        _mockUserRepo.Verify(r => r.AddAsync(
            It.Is<User>(u => u.Username == "testuser" && u.Email == "test@example.com"),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task Handle_ValidCommand_StoresRefreshTokenInCache()
    {
        SetupHappyPath();
        var cmd = new RegisterCommand("testuser", "test@example.com", "pass123", null);

        await _handler.Handle(cmd, CancellationToken.None);

        _mockCache.Verify(c => c.SetAsync(
            It.Is<string>(k => k.Contains("refresh_token_xyz")),
            It.IsAny<RefreshTokenEntry>(),
            It.IsAny<DistributedCacheEntryOptions?>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task Handle_ExistingUsername_ThrowsAppValidationException()
    {
        _mockUserRepo.Setup(r => r.ExistsByUsernameAsync("taken_user", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var cmd = new RegisterCommand("taken_user", "new@example.com", "pass123", null);

        var act = async () => await _handler.Handle(cmd, CancellationToken.None);

        await act.Should().ThrowAsync<AppValidationException>();
    }

    [Fact]
    public async Task Handle_ExistingEmail_ThrowsAppValidationException()
    {
        _mockUserRepo.Setup(r => r.ExistsByUsernameAsync("newuser", It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);
        _mockUserRepo.Setup(r => r.ExistsByEmailAsync("taken@example.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var cmd = new RegisterCommand("newuser", "taken@example.com", "pass123", null);

        var act = async () => await _handler.Handle(cmd, CancellationToken.None);

        await act.Should().ThrowAsync<AppValidationException>();
    }

    [Fact]
    public async Task Handle_ValidCommand_SetsExpiresAtInFuture()
    {
        SetupHappyPath();
        var cmd = new RegisterCommand("testuser", "test@example.com", "pass123", null);
        var before = DateTime.UtcNow;

        var result = await _handler.Handle(cmd, CancellationToken.None);

        result.ExpiresAt.Should().BeAfter(before);
    }

    [Fact]
    public async Task Handle_ValidCommand_SavesChangesOnce()
    {
        SetupHappyPath();
        var cmd = new RegisterCommand("testuser", "test@example.com", "pass123", null);

        await _handler.Handle(cmd, CancellationToken.None);

        _mockUow.Verify(u => u.SaveChangesAsync(It.IsAny<CancellationToken>()), Times.Once);
    }
}
