using ProblemService.Domain.Common;

namespace ProblemService.Domain.Entities;

public enum ProblemStatus
{
    Pending = 0,
    Processing = 1,
    Completed = 2,
    Failed = 3
}

public class Problem : BaseEntity
{
    private Problem() { } // For EF Core

    public Guid UserId { get; private set; }
    public string Title { get; private set; } = string.Empty;
    public string? Description { get; private set; }
    public string? ImagePath { get; private set; }
    public string? ExtractedText { get; private set; }
    public string Category { get; private set; } = "General";
    public string Difficulty { get; private set; } = "Medium";
    public ProblemStatus Status { get; private set; } = ProblemStatus.Pending;
    public DateTime? CompletedAt { get; private set; }

    public static Problem Create(Guid userId, string title, string? description, string? category, string? difficulty)
    {
        return new Problem
        {
            UserId = userId,
            Title = title,
            Description = description,
            Category = category ?? "General",
            Difficulty = difficulty ?? "Medium",
            Status = ProblemStatus.Pending
        };
    }

    public void Update(string? title, string? description, string? category, string? difficulty)
    {
        if (!string.IsNullOrEmpty(title)) Title = title;
        if (description != null) Description = description;
        if (!string.IsNullOrEmpty(category)) Category = category;
        if (!string.IsNullOrEmpty(difficulty)) Difficulty = difficulty;
        UpdatedAt = DateTime.UtcNow;
    }

    public void SetImage(string imagePath)
    {
        ImagePath = imagePath;
        Status = ProblemStatus.Processing;
        UpdatedAt = DateTime.UtcNow;
    }

    public void UpdateStatus(ProblemStatus status, string? extractedText = null)
    {
        Status = status;
        if (extractedText != null) ExtractedText = extractedText;
        if (status == ProblemStatus.Completed) CompletedAt = DateTime.UtcNow;
        UpdatedAt = DateTime.UtcNow;
    }

    public void SetProcessing()
    {
        Status = ProblemStatus.Processing;
        UpdatedAt = DateTime.UtcNow;
    }

    public void RevertToPending()
    {
        Status = ProblemStatus.Pending;
        UpdatedAt = DateTime.UtcNow;
    }
}
