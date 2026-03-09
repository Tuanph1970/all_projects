using ProblemService.Application.Common.Interfaces;
using ProblemService.Infrastructure.Persistence.Repositories;

namespace ProblemService.Infrastructure.Persistence;

public class UnitOfWork : IUnitOfWork
{
    private readonly ProblemDbContext _db;
    private ProblemRepository? _problems;
    private ProblemHistoryRepository? _histories;

    public UnitOfWork(ProblemDbContext db) => _db = db;

    public IProblemRepository Problems => _problems ??= new ProblemRepository(_db);
    public IProblemHistoryRepository ProblemHistories => _histories ??= new ProblemHistoryRepository(_db);

    public Task<int> SaveChangesAsync(CancellationToken ct = default) => _db.SaveChangesAsync(ct);
}
