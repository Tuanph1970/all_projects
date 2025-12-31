namespace Presentation.Models.Requests;

/// <summary>
/// Request model for getting user's problems with pagination and filters
/// </summary>
public class GetProblemsRequest
{
    /// <summary>
    /// Page number (default: 1)
    /// </summary>
    public int Page { get; set; } = 1;

    /// <summary>
    /// Items per page (default: 20, max: 100)
    /// </summary>
    public int Limit { get; set; } = 20;

    /// <summary>
    /// Filter by category
    /// </summary>
    public string? Category { get; set; }

    /// <summary>
    /// Filter by status (Pending, Processing, Completed, Failed)
    /// </summary>
    public string? Status { get; set; }

    /// <summary>
    /// Search query for description or category
    /// </summary>
    public string? SearchQuery { get; set; }
}
