using Domain.Entities;
using Domain.Enums;

namespace Application.Common.Interfaces;

public interface IProblemRepository : IRepository<Problem>
{
    Task<IEnumerable<Problem>> GetUserProblemsAsync(
        Guid userId,
        int skip,
        int take,
        string? category = null,
        ProblemStatus? status = null,
        string? searchQuery = null,
        CancellationToken cancellationToken = default);

    Task<int> GetUserProblemsCountAsync(
        Guid userId,
        string? category = null,
        ProblemStatus? status = null,
        string? searchQuery = null,
        CancellationToken cancellationToken = default);

    Task<Problem?> GetByIdWithSolutionAsync(Guid id, CancellationToken cancellationToken = default);
}
