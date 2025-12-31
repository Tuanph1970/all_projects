using Domain.Entities;

namespace Application.Common.Interfaces;

public interface IMLService
{
    Task<Solution?> SolveProblemAsync(Problem problem, CancellationToken cancellationToken = default);
}
