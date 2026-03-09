using AuthService.Application.Common.Interfaces;
using AuthService.Infrastructure.Persistence.Repositories;

namespace AuthService.Infrastructure.Persistence;

public class UnitOfWork : IUnitOfWork
{
    private readonly AuthDbContext _db;
    private UserRepository? _users;

    public UnitOfWork(AuthDbContext db) => _db = db;

    public IUserRepository Users => _users ??= new UserRepository(_db);

    public Task<int> SaveChangesAsync(CancellationToken ct = default)
        => _db.SaveChangesAsync(ct);

    public void Dispose() => _db.Dispose();
}
