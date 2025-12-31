using Domain.Common;
using Domain.ValueObjects;

namespace Domain.Entities;

public class Solution : BaseEntity
{
    public Guid ProblemId { get; private set; }
    public List<SolutionStep> Steps { get; private set; }
    public decimal Confidence { get; private set; }
    public string? AdditionalNotes { get; private set; }
    
    // Navigation property
    public virtual Problem Problem { get; private set; } = null!;
    
    private Solution()
    {
        Steps = new List<SolutionStep>();
    }
    
    public Solution(Guid problemId, List<SolutionStep> steps, decimal confidence, string? additionalNotes = null)
        : this()
    {
        ProblemId = problemId;
        Steps = steps ?? throw new ArgumentNullException(nameof(steps));
        Confidence = confidence;
        AdditionalNotes = additionalNotes;
        CreatedAt = DateTime.UtcNow;
        
        if (confidence < 0 || confidence > 1)
            throw new ArgumentException("Confidence must be between 0 and 1", nameof(confidence));
    }
    
    public void AddStep(SolutionStep step)
    {
        Steps.Add(step ?? throw new ArgumentNullException(nameof(step)));
        UpdatedAt = DateTime.UtcNow;
    }
    
    public void UpdateConfidence(decimal newConfidence)
    {
        if (newConfidence < 0 || newConfidence > 1)
            throw new ArgumentException("Confidence must be between 0 and 1", nameof(newConfidence));
            
        Confidence = newConfidence;
        UpdatedAt = DateTime.UtcNow;
    }
    
    public void AddNotes(string notes)
    {
        AdditionalNotes = notes;
        UpdatedAt = DateTime.UtcNow;
    }
}