using FluentAssertions;
using Moq;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Application.Features.Problems.Commands;
using ProblemService.Domain.Entities;

namespace ProblemService.Tests.Application.Commands;

public class CreateProblemCommandHandlerTests
{
    private readonly Mock<IUnitOfWork> _mockUow = new();
    private readonly Mock<IProblemRepository> _mockProblemRepo = new();
    private readonly Mock<IProblemHistoryRepository> _mockHistoryRepo = new();
    private readonly CreateProblemCommandHandler _handler;

    private static readonly Guid _userId = Guid.NewGuid();

    public CreateProblemCommandHandlerTests()
    {
        _mockUow.Setup(u => u.Problems).Returns(_mockProblemRepo.Object);
        _mockUow.Setup(u => u.ProblemHistories).Returns(_mockHistoryRepo.Object);
        _mockUow.Setup(u => u.SaveChangesAsync(It.IsAny<CancellationToken>())).ReturnsAsync(1);

        _handler = new CreateProblemCommandHandler(_mockUow.Object);
    }

    [Fact]
    public async Task Handle_ValidCommand_AddsProblemToRepository()
    {
        var cmd = new CreateProblemCommand(_userId, "Solve x", "2x + 3 = 7", "Algebra", "Easy");

        await _handler.Handle(cmd, CancellationToken.None);

        _mockProblemRepo.Verify(r => r.Add(
            It.Is<Problem>(p =>
                p.UserId == _userId &&
                p.Title == "Solve x" &&
                p.Category == "Algebra")),
            Times.Once);
    }

    [Fact]
    public async Task Handle_ValidCommand_ReturnsProblemDtoWithCorrectData()
    {
        var cmd = new CreateProblemCommand(_userId, "Find derivative", "f(x)=x^2", "Calculus", "Medium");

        var result = await _handler.Handle(cmd, CancellationToken.None);

        result.Should().NotBeNull();
        result.Title.Should().Be("Find derivative");
        result.Category.Should().Be("Calculus");
        result.Difficulty.Should().Be("Medium");
        result.UserId.Should().Be(_userId);
        result.Status.Should().Be("Pending");
    }

    [Fact]
    public async Task Handle_ValidCommand_CreatesHistoryEntry()
    {
        var cmd = new CreateProblemCommand(_userId, "Test Problem", null, null, null);

        await _handler.Handle(cmd, CancellationToken.None);

        _mockHistoryRepo.Verify(r => r.Add(
            It.Is<ProblemHistory>(h =>
                h.UserId == _userId &&
                h.Action == "Created")),
            Times.Once);
    }

    [Fact]
    public async Task Handle_NullCategory_UsesGeneralDefault()
    {
        var cmd = new CreateProblemCommand(_userId, "No category", null, null, null);

        var result = await _handler.Handle(cmd, CancellationToken.None);

        result.Category.Should().Be("General");
    }

    [Fact]
    public async Task Handle_NullDifficulty_UsesMediumDefault()
    {
        var cmd = new CreateProblemCommand(_userId, "No difficulty", null, null, null);

        var result = await _handler.Handle(cmd, CancellationToken.None);

        result.Difficulty.Should().Be("Medium");
    }

    [Fact]
    public async Task Handle_ValidCommand_SavesChanges()
    {
        var cmd = new CreateProblemCommand(_userId, "Title", null, "Algebra", "Easy");

        await _handler.Handle(cmd, CancellationToken.None);

        // SaveChanges called twice (once for problem, once for history)
        _mockUow.Verify(u => u.SaveChangesAsync(It.IsAny<CancellationToken>()), Times.Exactly(2));
    }

    [Fact]
    public async Task Handle_ValidCommand_ProblemHasNewId()
    {
        var cmd = new CreateProblemCommand(_userId, "Title", null, null, null);

        var result = await _handler.Handle(cmd, CancellationToken.None);

        result.Id.Should().NotBe(Guid.Empty);
    }
}
