using Microsoft.EntityFrameworkCore;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Domain.Entities;

namespace ProblemService.Infrastructure.Persistence.Repositories;

public class ProblemRepository : IProblemRepository
{
    private readonly ProblemDbContext _db;

    public ProblemRepository(ProblemDbContext db) => _db = db;

    public Task<Problem?> GetByIdAsync(Guid id, CancellationToken ct = default)
        => _db.Problems.FindAsync([id], ct).AsTask();

    public async Task<(List<Problem> Items, int TotalCount)> GetByUserIdAsync(
        Guid userId, int page, int pageSize, ProblemStatus? status, CancellationToken ct = default)
    {
        var query = _db.Problems.Where(p => p.UserId == userId);
        if (status.HasValue) query = query.Where(p => p.Status == status.Value);

        var total = await query.CountAsync(ct);
        var items = await query
            .OrderByDescending(p => p.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync(ct);

        return (items, total);
    }

    public void Add(Problem problem) => _db.Problems.Add(problem);
    public void Remove(Problem problem) => _db.Problems.Remove(problem);
}
