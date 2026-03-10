using FluentAssertions;
using Moq;
using ProblemService.Application.Common.Exceptions;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Application.Features.Problems.Queries;
using ProblemService.Domain.Entities;

namespace ProblemService.Tests.Application.Queries;

public class GetProblemByIdQueryHandlerTests
{
    private readonly Mock<IUnitOfWork> _mockUow = new();
    private readonly Mock<IProblemRepository> _mockProblemRepo = new();
    private readonly GetProblemByIdQueryHandler _handler;

    private static readonly Guid _userId = Guid.NewGuid();
    private static readonly Guid _problemId = Guid.NewGuid();

    public GetProblemByIdQueryHandlerTests()
    {
        _mockUow.Setup(u => u.Problems).Returns(_mockProblemRepo.Object);
        _handler = new GetProblemByIdQueryHandler(_mockUow.Object);
    }

    [Fact]
    public async Task Handle_ExistingProblem_ReturnsProblemDto()
    {
        var problem = Problem.Create(_userId, "Find the integral", "∫x²dx", "Calculus", "Hard");
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(problem);

        var result = await _handler.Handle(new GetProblemByIdQuery(_problemId), CancellationToken.None);

        result.Should().NotBeNull();
        result.Title.Should().Be("Find the integral");
        result.UserId.Should().Be(_userId);
        result.Status.Should().Be("Pending");
        result.Category.Should().Be("Calculus");
    }

    [Fact]
    public async Task Handle_ProblemNotFound_ThrowsNotFoundException()
    {
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync((Problem?)null);

        var act = async () => await _handler.Handle(
            new GetProblemByIdQuery(_problemId), CancellationToken.None);

        await act.Should().ThrowAsync<NotFoundException>();
    }

    [Fact]
    public async Task Handle_CompletedProblem_ReturnsCorrectStatus()
    {
        var problem = Problem.Create(_userId, "Title", null, "Algebra", "Easy");
        problem.UpdateStatus(ProblemStatus.Completed, "x = 3");
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(problem);

        var result = await _handler.Handle(new GetProblemByIdQuery(_problemId), CancellationToken.None);

        result.Status.Should().Be("Completed");
        result.ExtractedText.Should().Be("x = 3");
        result.CompletedAt.Should().NotBeNull();
    }

    [Fact]
    public async Task Handle_ProblemWithImage_ReturnsImageUrl()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        problem.SetImage("test-image.jpg");
        _mockProblemRepo.Setup(r => r.GetByIdAsync(_problemId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(problem);

        var result = await _handler.Handle(new GetProblemByIdQuery(_problemId), CancellationToken.None);

        result.ImageUrl.Should().NotBeNullOrEmpty();
        result.ImageUrl.Should().Contain("test-image.jpg");
    }
}
