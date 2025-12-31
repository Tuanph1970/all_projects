using Domain.ValueObjects;

namespace Application.DTOs;

public class SolutionDto
{
    public Guid Id { get; set; }
    public Guid ProblemId { get; set; }
    public List<SolutionStep> Steps { get; set; } = new();
    public decimal Confidence { get; set; }
    public string? AdditionalNotes { get; set; }
    public DateTime CreatedAt { get; set; }
}
