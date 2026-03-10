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

public class LoginCommandHandlerTests
{
    private readonly Mock<IUnitOfWork> _mockUow = new();
    private readonly Mock<IUserRepository> _mockUserRepo = new();
    private readonly Mock<IPasswordHasher> _mockHasher = new();
    private readonly Mock<IJwtTokenGenerator> _mockJwt = new();
    private readonly Mock<ICacheService> _mockCache = new();
    private readonly IConfiguration _config;
    private readonly ILogger<LoginCommandHandler> _logger;
    private readonly LoginCommandHandler _handler;

    private static User CreateActiveUser(string username = "testuser", string email = "test@example.com")
        => User.Create(username, email, "hashed_password", "Test User");

    public LoginCommandHandlerTests()
    {
        _config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Jwt:RefreshTokenExpirationDays"] = "7"
            })
            .Build();

        _logger = Mock.Of<ILogger<LoginCommandHandler>>();
        _mockUow.Setup(u => u.Users).Returns(_mockUserRepo.Object);

        _handler = new LoginCommandHandler(
            _mockUow.Object,
            _mockHasher.Object,
            _mockJwt.Object,
            _mockCache.Object,
            _config,
            _logger);
    }

    private void SetupTokenGeneration()
    {
        _mockJwt.Setup(j => j.GenerateAccessToken(It.IsAny<User>())).Returns("access_token");
        _mockJwt.Setup(j => j.GenerateRefreshToken()).Returns("refresh_token");
        _mockUow.Setup(u => u.SaveChangesAsync(It.IsAny<CancellationToken>())).ReturnsAsync(1);
        _mockCache.Setup(c => c.SetAsync(
            It.IsAny<string>(), It.IsAny<RefreshTokenEntry>(),
            It.IsAny<DistributedCacheEntryOptions?>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
    }

    [Fact]
    public async Task Handle_ValidCredentials_ReturnsAuthResultDtoWithTokens()
    {
        var user = CreateActiveUser();
        _mockUserRepo.Setup(r => r.GetByUsernameOrEmailAsync("testuser", It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);
        _mockHasher.Setup(h => h.Verify("correct_password", "hashed_password")).Returns(true);
        SetupTokenGeneration();

        var result = await _handler.Handle(new LoginCommand("testuser", "correct_password"), CancellationToken.None);

        result.Should().NotBeNull();
        result.AccessToken.Should().Be("access_token");
        result.RefreshToken.Should().Be("refresh_token");
        result.Username.Should().Be("testuser");
    }

    [Fact]
    public async Task Handle_UserNotFound_ThrowsUnauthorizedException()
    {
        _mockUserRepo.Setup(r => r.GetByUsernameOrEmailAsync("ghost", It.IsAny<CancellationToken>()))
            .ReturnsAsync((User?)null);

        var act = async () => await _handler.Handle(new LoginCommand("ghost", "anypass"), CancellationToken.None);

        await act.Should().ThrowAsync<UnauthorizedException>();
    }

    [Fact]
    public async Task Handle_WrongPassword_ThrowsUnauthorizedException()
    {
        var user = CreateActiveUser();
        _mockUserRepo.Setup(r => r.GetByUsernameOrEmailAsync("testuser", It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);
        _mockHasher.Setup(h => h.Verify("wrong_password", "hashed_password")).Returns(false);

        var act = async () => await _handler.Handle(new LoginCommand("testuser", "wrong_password"), CancellationToken.None);

        await act.Should().ThrowAsync<UnauthorizedException>();
    }

    [Fact]
    public async Task Handle_InactiveUser_ThrowsUnauthorizedException()
    {
        var user = CreateActiveUser();
        user.Deactivate();

        _mockUserRepo.Setup(r => r.GetByUsernameOrEmailAsync("testuser", It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);
        _mockHasher.Setup(h => h.Verify(It.IsAny<string>(), It.IsAny<string>())).Returns(true);

        var act = async () => await _handler.Handle(new LoginCommand("testuser", "pass"), CancellationToken.None);

        await act.Should().ThrowAsync<UnauthorizedException>();
    }

    [Fact]
    public async Task Handle_ValidLogin_StoresRefreshTokenInCache()
    {
        var user = CreateActiveUser();
        _mockUserRepo.Setup(r => r.GetByUsernameOrEmailAsync("testuser", It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);
        _mockHasher.Setup(h => h.Verify(It.IsAny<string>(), It.IsAny<string>())).Returns(true);
        SetupTokenGeneration();

        await _handler.Handle(new LoginCommand("testuser", "pass"), CancellationToken.None);

        _mockCache.Verify(c => c.SetAsync(
            It.Is<string>(k => k.Contains("refresh_token")),
            It.IsAny<RefreshTokenEntry>(),
            It.IsAny<DistributedCacheEntryOptions?>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task Handle_ValidLogin_SavesChanges()
    {
        var user = CreateActiveUser();
        _mockUserRepo.Setup(r => r.GetByUsernameOrEmailAsync("testuser", It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);
        _mockHasher.Setup(h => h.Verify(It.IsAny<string>(), It.IsAny<string>())).Returns(true);
        SetupTokenGeneration();

        await _handler.Handle(new LoginCommand("testuser", "pass"), CancellationToken.None);

        _mockUow.Verify(u => u.SaveChangesAsync(It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task Handle_ValidEmailLogin_Succeeds()
    {
        var user = CreateActiveUser();
        _mockUserRepo.Setup(r => r.GetByUsernameOrEmailAsync("test@example.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);
        _mockHasher.Setup(h => h.Verify(It.IsAny<string>(), It.IsAny<string>())).Returns(true);
        SetupTokenGeneration();

        var result = await _handler.Handle(new LoginCommand("test@example.com", "pass"), CancellationToken.None);

        result.Should().NotBeNull();
        result.Email.Should().Be("test@example.com");
    }
}
