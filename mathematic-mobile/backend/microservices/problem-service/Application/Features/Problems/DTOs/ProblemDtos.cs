namespace ProblemService.Application.Features.Problems.DTOs;

public record ProblemDto(
    Guid Id,
    Guid UserId,
    string Title,
    string? Description,
    string? ImageUrl,
    string? ExtractedText,
    string Category,
    string Difficulty,
    string Status,
    DateTime CreatedAt,
    DateTime? CompletedAt
);

public record ProblemListDto(
    List<ProblemDto> Problems,
    int TotalCount,
    int Page,
    int PageSize
);
