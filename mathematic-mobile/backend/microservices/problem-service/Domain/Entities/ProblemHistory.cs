using ProblemService.Domain.Common;

namespace ProblemService.Domain.Entities;

public class ProblemHistory : BaseEntity
{
    private ProblemHistory() { } // For EF Core

    public Guid ProblemId { get; private set; }
    public Guid UserId { get; private set; }
    public string Action { get; private set; } = string.Empty;
    public string? Details { get; private set; }

    public static ProblemHistory Create(Guid problemId, Guid userId, string action, string? details = null)
    {
        return new ProblemHistory
        {
            ProblemId = problemId,
            UserId = userId,
            Action = action,
            Details = details
        };
    }
}
