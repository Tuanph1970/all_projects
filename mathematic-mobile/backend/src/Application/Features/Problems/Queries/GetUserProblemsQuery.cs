using Application.Common.Interfaces;
using Application.DTOs;

namespace Application.Features.Problems.Queries;

public class GetUserProblemsQuery : IQuery<PaginatedResult<ProblemDto>>
{
    public Guid UserId { get; set; }
    public int Page { get; set; } = 1;
    public int Limit { get; set; } = 20;
    public string? Category { get; set; }
    public string? Status { get; set; }
    public string? SearchQuery { get; set; }
}
