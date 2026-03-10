using AuthService.Application.Common.Exceptions;
using AuthService.Application.Common.Interfaces;
using AuthService.Application.Features.Authentication.Queries;
using AuthService.Domain.Entities;
using FluentAssertions;
using Moq;

namespace AuthService.Tests.Application.Queries;

public class GetCurrentUserQueryHandlerTests
{
    private readonly Mock<IUnitOfWork> _mockUow = new();
    private readonly Mock<IUserRepository> _mockUserRepo = new();
    private readonly GetCurrentUserQueryHandler _handler;

    public GetCurrentUserQueryHandlerTests()
    {
        _mockUow.Setup(u => u.Users).Returns(_mockUserRepo.Object);
        _handler = new GetCurrentUserQueryHandler(_mockUow.Object);
    }

    // ── Happy path ───────────────────────────────────────────────

    [Fact]
    public async Task ExistingUser_ReturnsUserDto()
    {
        var userId = Guid.NewGuid();
        var user = User.Create("john", "john@example.com", "hashedpw", "John Doe");
        typeof(User).GetProperty("Id")!.SetValue(user, userId);

        _mockUserRepo
            .Setup(r => r.GetByIdAsync(userId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);

        var result = await _handler.Handle(new GetCurrentUserQuery(userId), CancellationToken.None);

        result.Should().NotBeNull();
        result.Id.Should().Be(userId);
        result.Username.Should().Be("john");
        result.Email.Should().Be("john@example.com");
    }

    [Fact]
    public async Task ExistingUser_ReturnsCorrectFullName()
    {
        var userId = Guid.NewGuid();
        var user = User.Create("jane", "jane@example.com", "hashedpw", "Jane Smith");
        typeof(User).GetProperty("Id")!.SetValue(user, userId);

        _mockUserRepo
            .Setup(r => r.GetByIdAsync(userId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);

        var result = await _handler.Handle(new GetCurrentUserQuery(userId), CancellationToken.None);

        result.FullName.Should().Be("Jane Smith");
    }

    [Fact]
    public async Task ExistingUser_ReturnsCorrectRole()
    {
        var userId = Guid.NewGuid();
        var user = User.Create("admin", "admin@example.com", "hashedpw", "Admin User");
        typeof(User).GetProperty("Id")!.SetValue(user, userId);

        _mockUserRepo
            .Setup(r => r.GetByIdAsync(userId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);

        var result = await _handler.Handle(new GetCurrentUserQuery(userId), CancellationToken.None);

        result.Role.Should().Be(user.Role);
    }

    [Fact]
    public async Task ExistingUser_IsActiveIsCorrect()
    {
        var userId = Guid.NewGuid();
        var user = User.Create("active_user", "active@example.com", "hashedpw", null);
        typeof(User).GetProperty("Id")!.SetValue(user, userId);

        _mockUserRepo
            .Setup(r => r.GetByIdAsync(userId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);

        var result = await _handler.Handle(new GetCurrentUserQuery(userId), CancellationToken.None);

        result.IsActive.Should().Be(user.IsActive);
    }

    [Fact]
    public async Task ExistingUser_ReturnsCreatedAt()
    {
        var userId = Guid.NewGuid();
        var user = User.Create("user1", "user1@example.com", "hash", null);
        typeof(User).GetProperty("Id")!.SetValue(user, userId);

        _mockUserRepo
            .Setup(r => r.GetByIdAsync(userId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);

        var result = await _handler.Handle(new GetCurrentUserQuery(userId), CancellationToken.None);

        result.CreatedAt.Should().BeCloseTo(DateTime.UtcNow, TimeSpan.FromSeconds(5));
    }

    // ── Error cases ──────────────────────────────────────────────

    [Fact]
    public async Task UserNotFound_ThrowsNotFoundException()
    {
        var userId = Guid.NewGuid();

        _mockUserRepo
            .Setup(r => r.GetByIdAsync(userId, It.IsAny<CancellationToken>()))
            .ReturnsAsync((User?)null);

        Func<Task> act = () => _handler.Handle(new GetCurrentUserQuery(userId), CancellationToken.None);

        await act.Should().ThrowAsync<NotFoundException>();
    }

    [Fact]
    public async Task UserNotFound_ExceptionMessageContainsUserId()
    {
        var userId = Guid.NewGuid();

        _mockUserRepo
            .Setup(r => r.GetByIdAsync(userId, It.IsAny<CancellationToken>()))
            .ReturnsAsync((User?)null);

        Func<Task> act = () => _handler.Handle(new GetCurrentUserQuery(userId), CancellationToken.None);

        var ex = await act.Should().ThrowAsync<NotFoundException>();
        ex.WithMessage($"*{userId}*");
    }

    // ── Cancellation ─────────────────────────────────────────────

    [Fact]
    public async Task Handle_PassesCancellationTokenToRepository()
    {
        var userId = Guid.NewGuid();
        var user = User.Create("user", "u@e.com", "hash", null);
        typeof(User).GetProperty("Id")!.SetValue(user, userId);
        var cts = new CancellationTokenSource();

        _mockUserRepo
            .Setup(r => r.GetByIdAsync(userId, cts.Token))
            .ReturnsAsync(user);

        await _handler.Handle(new GetCurrentUserQuery(userId), cts.Token);

        _mockUserRepo.Verify(r => r.GetByIdAsync(userId, cts.Token), Times.Once);
    }
}
