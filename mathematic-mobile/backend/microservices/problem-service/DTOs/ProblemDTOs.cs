using System.ComponentModel.DataAnnotations;
using ProblemService.Models;

namespace ProblemService.DTOs;

public record CreateProblemRequest(
    [Required][StringLength(200)] string Title,
    string? Description,
    string? Category,
    string? Difficulty
);

public record UpdateProblemRequest(
    string? Title,
    string? Description,
    string? Category,
    string? Difficulty
);

public record ProblemResponse(
    int Id,
    int UserId,
    string Title,
    string? Description,
    string? ImageUrl,
    string? ExtractedText,
    string Category,
    string Difficulty,
    string Status,
    DateTime CreatedAt,
    DateTime? SolvedAt
);

public record ProblemListResponse(
    List<ProblemResponse> Problems,
    int TotalCount,
    int Page,
    int PageSize
);

public record ImageUploadResponse(
    bool Success,
    string? ImagePath,
    string? ExtractedText,
    string Message
);

public record ProcessProblemRequest(
    int ProblemId,
    string? ExtractedText
);

public record ProblemStatusUpdate(
    int ProblemId,
    ProblemStatus Status,
    string? ExtractedText = null
);
