using ProblemService.Application.Features.Problems.DTOs;
using ProblemService.Domain.Entities;

namespace ProblemService.Application.Features.Problems.Extensions;

internal static class ProblemMappingExtensions
{
    internal static ProblemDto ToDto(this Problem problem) => new(
        problem.Id,
        problem.UserId,
        problem.Title,
        problem.Description,
        problem.ImagePath != null ? $"/uploads/{problem.ImagePath}" : null,
        problem.ExtractedText,
        problem.Category,
        problem.Difficulty,
        problem.Status.ToString(),
        problem.CreatedAt,
        problem.CompletedAt
    );
}
