using Domain.Common;
using Domain.Enums;
using Domain.ValueObjects;

namespace Domain.Entities;

public class Problem : BaseEntity
{
    public Guid UserId { get; private set; }
    public string ImageUrl { get; private set; } = string.Empty;
    public string Category { get; private set; } = string.Empty;
    public ProblemStatus Status { get; private set; }
    public string? Description { get; private set; }
    
    // Navigation properties
    public virtual User User { get; private set; } = null!;
    public virtual Solution? Solution { get; private set; }
    
    private Problem()
    {
        // Private constructor for EF Core
    }
    
    public Problem(Guid userId, string imageUrl, string category, string? description = null)
    {
        UserId = userId;
        ImageUrl = imageUrl ?? throw new ArgumentNullException(nameof(imageUrl));
        Category = category ?? throw new ArgumentNullException(nameof(category));
        Description = description;
        Status = ProblemStatus.Pending;
        CreatedAt = DateTime.UtcNow;
    }
    
    public void MarkAsProcessing()
    {
        Status = ProblemStatus.Processing;
        UpdatedAt = DateTime.UtcNow;
    }
    
    public void MarkAsCompleted(Solution solution)
    {
        Status = ProblemStatus.Completed;
        Solution = solution ?? throw new ArgumentNullException(nameof(solution));
        UpdatedAt = DateTime.UtcNow;
    }
    
    public void MarkAsFailed(string? errorMessage = null)
    {
        Status = ProblemStatus.Failed;
        Description = errorMessage ?? Description;
        UpdatedAt = DateTime.UtcNow;
    }
    
    public void UpdateDescription(string description)
    {
        Description = description;
        UpdatedAt = DateTime.UtcNow;
    }
}