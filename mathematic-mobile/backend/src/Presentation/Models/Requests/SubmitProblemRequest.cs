namespace Presentation.Models.Requests;

/// <summary>
/// Request model for submitting a new math problem
/// </summary>
public class SubmitProblemRequest
{
    /// <summary>
    /// Image file containing the mathematical problem
    /// </summary>
    public IFormFile ImageFile { get; set; } = null!;

    /// <summary>
    /// Category of the problem (e.g., Algebra, Geometry, Calculus)
    /// </summary>
    public string Category { get; set; } = string.Empty;

    /// <summary>
    /// Optional description or additional context
    /// </summary>
    public string? Description { get; set; }
}
