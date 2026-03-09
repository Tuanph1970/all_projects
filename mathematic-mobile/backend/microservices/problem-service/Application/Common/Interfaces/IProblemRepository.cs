using ProblemService.Domain.Entities;

namespace ProblemService.Application.Common.Interfaces;

public interface IProblemRepository
{
    Task<Problem?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<(List<Problem> Items, int TotalCount)> GetByUserIdAsync(Guid userId, int page, int pageSize, ProblemStatus? status, CancellationToken ct = default);
    void Add(Problem problem);
    void Remove(Problem problem);
}
