using Application.Common.Interfaces;
using Application.DTOs;

namespace Application.Features.Problems.Commands;

public class RetryProblemCommand : ICommand<ProblemResult>
{
    public Guid ProblemId { get; set; }
    public Guid UserId { get; set; }
}
