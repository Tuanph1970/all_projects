using FluentAssertions;
using Moq;
using ProblemService.Application.Common.Exceptions;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Application.Features.Problems.Commands;
using ProblemService.Domain.Entities;

namespace ProblemService.Tests.Application.Commands;

public class DeleteProblemCommandHandlerTests
{
    private readonly Mock<IUnitOfWork> _mockUow = new();
    private readonly Mock<IProblemRepository> _mockProblemRepo = new();
    private readonly DeleteProblemCommandHandler _handler;

    private static readonly Guid _userId = Guid.NewGuid();
    private static readonly Guid _problemId = Guid.NewGuid();
    private static readonly Guid _otherUserId = Guid.NewGuid();

    public DeleteProblemCommandHandlerTests()
    {
        _mockUow.Setup(u => u.Problems).Returns(_mockProblemRepo.Object);
        _mockUow.Setup(u => u.SaveChangesAsync(It.IsAny<CancellationToken>())).ReturnsAsync(1);
        _handler = new DeleteProblemCommandHandler(_mockUow.Object);
    }

    [Fact]
    public async Task Handle_ValidCommand_RemovesProblemFromRepository()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(problem);

        await _handler.Handle(new DeleteProblemCommand(_problemId, _userId), CancellationToken.None);

        _mockProblemRepo.Verify(r => r.Remove(problem), Times.Once);
    }

    [Fact]
    public async Task Handle_ValidCommand_SavesChanges()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(problem);

        await _handler.Handle(new DeleteProblemCommand(_problemId, _userId), CancellationToken.None);

        _mockUow.Verify(u => u.SaveChangesAsync(It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task Handle_ProblemNotFound_ThrowsNotFoundException()
    {
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync((Problem?)null);

        var act = async () => await _handler.Handle(
            new DeleteProblemCommand(_problemId, _userId), CancellationToken.None);

        await act.Should().ThrowAsync<NotFoundException>();
    }

    [Fact]
    public async Task Handle_DifferentUserId_ThrowsUnauthorizedException()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(problem);

        var act = async () => await _handler.Handle(
            new DeleteProblemCommand(_problemId, _otherUserId), CancellationToken.None);

        await act.Should().ThrowAsync<UnauthorizedException>();
    }
}
