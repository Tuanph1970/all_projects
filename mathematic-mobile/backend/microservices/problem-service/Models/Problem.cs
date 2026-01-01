namespace ProblemService.Models;

public class Problem
{
    public int Id { get; set; }
    public int UserId { get; set; }
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string? ImagePath { get; set; }
    public string? ExtractedText { get; set; }
    public string Category { get; set; } = "General";
    public string Difficulty { get; set; } = "Medium";
    public ProblemStatus Status { get; set; } = ProblemStatus.Pending;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? UpdatedAt { get; set; }
    public DateTime? SolvedAt { get; set; }
}

public enum ProblemStatus
{
    Pending = 0,
    Processing = 1,
    Solved = 2,
    Failed = 3
}

public class ProblemHistory
{
    public int Id { get; set; }
    public int ProblemId { get; set; }
    public int UserId { get; set; }
    public string Action { get; set; } = string.Empty;
    public string? Details { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
