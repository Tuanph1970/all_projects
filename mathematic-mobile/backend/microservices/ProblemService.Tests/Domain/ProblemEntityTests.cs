using FluentAssertions;
using ProblemService.Domain.Entities;

namespace ProblemService.Tests.Domain;

public class ProblemEntityTests
{
    private static readonly Guid _userId = Guid.NewGuid();

    // ── Create ────────────────────────────────────────────────────

    [Fact]
    public void Create_ValidData_SetsPropertiesCorrectly()
    {
        var problem = Problem.Create(_userId, "Solve x", "Find x in 2x=4", "Algebra", "Easy");

        problem.UserId.Should().Be(_userId);
        problem.Title.Should().Be("Solve x");
        problem.Description.Should().Be("Find x in 2x=4");
        problem.Category.Should().Be("Algebra");
        problem.Difficulty.Should().Be("Easy");
        problem.Status.Should().Be(ProblemStatus.Pending);
        problem.Id.Should().NotBe(Guid.Empty);
        problem.CompletedAt.Should().BeNull();
        problem.ImagePath.Should().BeNull();
        problem.ExtractedText.Should().BeNull();
    }

    [Fact]
    public void Create_NullCategory_DefaultsToGeneral()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        problem.Category.Should().Be("General");
    }

    [Fact]
    public void Create_NullDifficulty_DefaultsToMedium()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        problem.Difficulty.Should().Be("Medium");
    }

    [Fact]
    public void Create_InitialStatus_IsPending()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        problem.Status.Should().Be(ProblemStatus.Pending);
    }

    [Fact]
    public void Create_SetsCreatedAt()
    {
        var before = DateTime.UtcNow;
        var problem = Problem.Create(_userId, "Title", null, null, null);
        problem.CreatedAt.Should().BeOnOrAfter(before);
    }

    [Fact]
    public void Create_TwoProblems_HaveUniqueIds()
    {
        var p1 = Problem.Create(_userId, "P1", null, null, null);
        var p2 = Problem.Create(_userId, "P2", null, null, null);
        p1.Id.Should().NotBe(p2.Id);
    }

    // ── Update ────────────────────────────────────────────────────

    [Fact]
    public void Update_WithAllFields_UpdatesAll()
    {
        var problem = Problem.Create(_userId, "Old Title", "Old Desc", "Algebra", "Easy");

        problem.Update("New Title", "New Desc", "Geometry", "Hard");

        problem.Title.Should().Be("New Title");
        problem.Description.Should().Be("New Desc");
        problem.Category.Should().Be("Geometry");
        problem.Difficulty.Should().Be("Hard");
    }

    [Fact]
    public void Update_NullTitle_KeepsOriginalTitle()
    {
        var problem = Problem.Create(_userId, "Original Title", null, null, null);

        problem.Update(null, "New Desc", null, null);

        problem.Title.Should().Be("Original Title");
    }

    [Fact]
    public void Update_EmptyTitle_KeepsOriginalTitle()
    {
        var problem = Problem.Create(_userId, "Original Title", null, null, null);

        problem.Update("", null, null, null);

        problem.Title.Should().Be("Original Title");
    }

    [Fact]
    public void Update_SetsUpdatedAt()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        var before = DateTime.UtcNow;

        problem.Update("New Title", null, null, null);

        problem.UpdatedAt.Should().NotBeNull();
        problem.UpdatedAt.Should().BeOnOrAfter(before);
    }

    // ── SetImage ──────────────────────────────────────────────────

    [Fact]
    public void SetImage_SetsImagePathAndChangesStatusToProcessing()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);

        problem.SetImage("uploads/image.jpg");

        problem.ImagePath.Should().Be("uploads/image.jpg");
        problem.Status.Should().Be(ProblemStatus.Processing);
    }

    [Fact]
    public void SetImage_SetsUpdatedAt()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        var before = DateTime.UtcNow;

        problem.SetImage("image.png");

        problem.UpdatedAt.Should().NotBeNull();
        problem.UpdatedAt.Should().BeOnOrAfter(before);
    }

    // ── UpdateStatus ──────────────────────────────────────────────

    [Fact]
    public void UpdateStatus_ToCompleted_SetsCompletedAt()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        var before = DateTime.UtcNow;

        problem.UpdateStatus(ProblemStatus.Completed);

        problem.Status.Should().Be(ProblemStatus.Completed);
        problem.CompletedAt.Should().NotBeNull();
        problem.CompletedAt.Should().BeOnOrAfter(before);
    }

    [Fact]
    public void UpdateStatus_ToFailed_DoesNotSetCompletedAt()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);

        problem.UpdateStatus(ProblemStatus.Failed);

        problem.Status.Should().Be(ProblemStatus.Failed);
        problem.CompletedAt.Should().BeNull();
    }

    [Fact]
    public void UpdateStatus_WithExtractedText_SetsExtractedText()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);

        problem.UpdateStatus(ProblemStatus.Completed, "2x = 4");

        problem.ExtractedText.Should().Be("2x = 4");
    }

    [Fact]
    public void UpdateStatus_WithoutExtractedText_KeepsNull()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);

        problem.UpdateStatus(ProblemStatus.Failed);

        problem.ExtractedText.Should().BeNull();
    }

    [Fact]
    public void UpdateStatus_SetsUpdatedAt()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        var before = DateTime.UtcNow;

        problem.UpdateStatus(ProblemStatus.Processing);

        problem.UpdatedAt.Should().NotBeNull();
        problem.UpdatedAt.Should().BeOnOrAfter(before);
    }

    // ── SetProcessing ─────────────────────────────────────────────

    [Fact]
    public void SetProcessing_SetsStatusToProcessing()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        problem.Status.Should().Be(ProblemStatus.Pending);

        problem.SetProcessing();

        problem.Status.Should().Be(ProblemStatus.Processing);
    }

    // ── RevertToPending ───────────────────────────────────────────

    [Fact]
    public void RevertToPending_SetsStatusBackToPending()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        problem.SetProcessing();
        problem.Status.Should().Be(ProblemStatus.Processing);

        problem.RevertToPending();

        problem.Status.Should().Be(ProblemStatus.Pending);
    }

    [Fact]
    public void RevertToPending_SetsUpdatedAt()
    {
        var problem = Problem.Create(_userId, "Title", null, null, null);
        problem.SetProcessing();
        var before = DateTime.UtcNow;

        problem.RevertToPending();

        problem.UpdatedAt.Should().NotBeNull();
        problem.UpdatedAt.Should().BeOnOrAfter(before);
    }
}
