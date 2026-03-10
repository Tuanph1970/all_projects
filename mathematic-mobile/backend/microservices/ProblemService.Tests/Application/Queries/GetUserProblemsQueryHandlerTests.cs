using FluentAssertions;
using Moq;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Application.Features.Problems.Queries;
using ProblemService.Domain.Entities;

namespace ProblemService.Tests.Application.Queries;

public class GetUserProblemsQueryHandlerTests
{
    private readonly Mock<IUnitOfWork> _mockUow = new();
    private readonly Mock<IProblemRepository> _mockProblemRepo = new();
    private readonly GetUserProblemsQueryHandler _handler;

    private static readonly Guid _userId = Guid.NewGuid();

    public GetUserProblemsQueryHandlerTests()
    {
        _mockUow.Setup(u => u.Problems).Returns(_mockProblemRepo.Object);
        _handler = new GetUserProblemsQueryHandler(_mockUow.Object);
    }

    private static List<Problem> CreateProblems(int count, Guid userId)
    {
        return Enumerable.Range(0, count)
            .Select(i => Problem.Create(userId, $"Problem {i}", null, "Algebra", "Easy"))
            .ToList();
    }

    [Fact]
    public async Task Handle_ValidQuery_ReturnsPaginatedList()
    {
        var problems = CreateProblems(3, _userId);
        _mockProblemRepo.Setup(r => r.GetByUserIdAsync(
            _userId, 1, 10, null, It.IsAny<CancellationToken>()))
            .ReturnsAsync((problems, 3));

        var result = await _handler.Handle(
            new GetUserProblemsQuery(_userId, 1, 10, null), CancellationToken.None);

        result.Should().NotBeNull();
        result.Problems.Should().HaveCount(3);
        result.TotalCount.Should().Be(3);
        result.Page.Should().Be(1);
        result.PageSize.Should().Be(10);
    }

    [Fact]
    public async Task Handle_EmptyResult_ReturnsEmptyList()
    {
        _mockProblemRepo.Setup(r => r.GetByUserIdAsync(
            _userId, 1, 10, null, It.IsAny<CancellationToken>()))
            .ReturnsAsync((new List<Problem>(), 0));

        var result = await _handler.Handle(
            new GetUserProblemsQuery(_userId, 1, 10, null), CancellationToken.None);

        result.Problems.Should().BeEmpty();
        result.TotalCount.Should().Be(0);
    }

    [Theory]
    [InlineData("Pending", ProblemStatus.Pending)]
    [InlineData("Processing", ProblemStatus.Processing)]
    [InlineData("Completed", ProblemStatus.Completed)]
    [InlineData("Failed", ProblemStatus.Failed)]
    public async Task Handle_ValidStatusFilter_ParsesStatusCorrectly(string statusStr, ProblemStatus expectedStatus)
    {
        _mockProblemRepo.Setup(r => r.GetByUserIdAsync(
            _userId, 1, 10, expectedStatus, It.IsAny<CancellationToken>()))
            .ReturnsAsync((new List<Problem>(), 0));

        await _handler.Handle(
            new GetUserProblemsQuery(_userId, 1, 10, statusStr), CancellationToken.None);

        _mockProblemRepo.Verify(r => r.GetByUserIdAsync(
            _userId, 1, 10, expectedStatus, It.IsAny<CancellationToken>()), Times.Once);
    }

    [Theory]
    [InlineData("invalid_status")]
    [InlineData("UNKNOWN")]
    [InlineData("")]
    public async Task Handle_InvalidStatusFilter_PassesNullStatus(string invalidStatus)
    {
        _mockProblemRepo.Setup(r => r.GetByUserIdAsync(
            _userId, 1, 10, null, It.IsAny<CancellationToken>()))
            .ReturnsAsync((new List<Problem>(), 0));

        await _handler.Handle(
            new GetUserProblemsQuery(_userId, 1, 10, invalidStatus), CancellationToken.None);

        _mockProblemRepo.Verify(r => r.GetByUserIdAsync(
            _userId, 1, 10, null, It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task Handle_ValidQuery_ReturnsDtosWithCorrectFields()
    {
        var problem = Problem.Create(_userId, "Algebra Problem", "Solve x", "Algebra", "Hard");
        _mockProblemRepo.Setup(r => r.GetByUserIdAsync(
            _userId, 1, 10, null, It.IsAny<CancellationToken>()))
            .ReturnsAsync((new List<Problem> { problem }, 1));

        var result = await _handler.Handle(
            new GetUserProblemsQuery(_userId, 1, 10, null), CancellationToken.None);

        var dto = result.Problems.Single();
        dto.Title.Should().Be("Algebra Problem");
        dto.UserId.Should().Be(_userId);
        dto.Status.Should().Be("Pending");
        dto.Category.Should().Be("Algebra");
    }

    [Fact]
    public async Task Handle_SecondPage_ReturnsCorrectPaginationInfo()
    {
        _mockProblemRepo.Setup(r => r.GetByUserIdAsync(
            _userId, 2, 5, null, It.IsAny<CancellationToken>()))
            .ReturnsAsync((new List<Problem>(), 15));

        var result = await _handler.Handle(
            new GetUserProblemsQuery(_userId, 2, 5, null), CancellationToken.None);

        result.Page.Should().Be(2);
        result.PageSize.Should().Be(5);
        result.TotalCount.Should().Be(15);
    }
}
