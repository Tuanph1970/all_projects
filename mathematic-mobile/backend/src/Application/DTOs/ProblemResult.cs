namespace Application.DTOs;

public class ProblemResult
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
    public ProblemDto? Problem { get; set; }
}
