using FluentAssertions;
using Moq;
using ProblemService.Application.Common.Exceptions;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Application.Features.Problems.Commands;
using ProblemService.Domain.Entities;

namespace ProblemService.Tests.Application.Commands;

public class UpdateProblemCommandHandlerTests
{
    private readonly Mock<IUnitOfWork> _mockUow = new();
    private readonly Mock<IProblemRepository> _mockProblemRepo = new();
    private readonly UpdateProblemCommandHandler _handler;

    private static readonly Guid _userId = Guid.NewGuid();
    private static readonly Guid _problemId = Guid.NewGuid();
    private static readonly Guid _otherUserId = Guid.NewGuid();

    public UpdateProblemCommandHandlerTests()
    {
        _mockUow.Setup(u => u.Problems).Returns(_mockProblemRepo.Object);
        _mockUow.Setup(u => u.SaveChangesAsync(It.IsAny<CancellationToken>())).ReturnsAsync(1);
        _handler = new UpdateProblemCommandHandler(_mockUow.Object);
    }

    private Problem CreateProblemForUser(Guid userId)
    {
        // Reflection to set UserId since Problem has private setters
        var problem = Problem.Create(userId, "Original Title", "Original Desc", "Algebra", "Easy");
        return problem;
    }

    [Fact]
    public async Task Handle_ValidCommand_UpdatesProblemSuccessfully()
    {
        var problem = CreateProblemForUser(_userId);
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(problem);

        var cmd = new UpdateProblemCommand(_problemId, _userId, "New Title", "New Desc", "Geometry", "Hard");

        await _handler.Handle(cmd, CancellationToken.None);

        problem.Title.Should().Be("New Title");
        problem.Category.Should().Be("Geometry");
    }

    [Fact]
    public async Task Handle_ValidCommand_SavesChanges()
    {
        var problem = CreateProblemForUser(_userId);
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(problem);

        await _handler.Handle(new UpdateProblemCommand(_problemId, _userId, "New Title", null, null, null), CancellationToken.None);

        _mockUow.Verify(u => u.SaveChangesAsync(It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task Handle_ProblemNotFound_ThrowsNotFoundException()
    {
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync((Problem?)null);

        var act = async () => await _handler.Handle(
            new UpdateProblemCommand(_problemId, _userId, "Title", null, null, null), CancellationToken.None);

        await act.Should().ThrowAsync<NotFoundException>();
    }

    [Fact]
    public async Task Handle_DifferentUserId_ThrowsUnauthorizedException()
    {
        var problem = CreateProblemForUser(_userId);
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(problem);

        var act = async () => await _handler.Handle(
            new UpdateProblemCommand(_problemId, _otherUserId, "Title", null, null, null), CancellationToken.None);

        await act.Should().ThrowAsync<UnauthorizedException>();
    }
}
