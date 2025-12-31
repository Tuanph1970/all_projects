using Application.Common.Interfaces;
using Application.DTOs;

namespace Application.Features.Problems.Queries;

public class GetProblemByIdQuery : IQuery<ProblemDto?>
{
    public Guid ProblemId { get; set; }
    public Guid UserId { get; set; }
}
