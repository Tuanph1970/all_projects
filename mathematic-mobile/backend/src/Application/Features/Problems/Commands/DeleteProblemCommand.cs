using Application.Common.Interfaces;

namespace Application.Features.Problems.Commands;

public class DeleteProblemCommand : ICommand<bool>
{
    public Guid ProblemId { get; set; }
    public Guid UserId { get; set; }
}
