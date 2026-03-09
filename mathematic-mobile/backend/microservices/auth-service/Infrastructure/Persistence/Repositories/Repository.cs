using Microsoft.EntityFrameworkCore;
using AuthService.Application.Common.Interfaces;
using AuthService.Domain.Common;

namespace AuthService.Infrastructure.Persistence.Repositories;

public abstract class Repository<T> : IRepository<T> where T : BaseEntity
{
    protected readonly AuthDbContext _db;
    protected readonly DbSet<T> _set;

    protected Repository(AuthDbContext db) { _db = db; _set = db.Set<T>(); }

    public virtual Task<T?> GetByIdAsync(Guid id, CancellationToken ct = default)
        => _set.FindAsync([id], ct).AsTask();

    public virtual async Task<IEnumerable<T>> GetAllAsync(CancellationToken ct = default)
        => await _set.ToListAsync(ct);

    public virtual async Task AddAsync(T entity, CancellationToken ct = default)
        => await _set.AddAsync(entity, ct);

    public virtual void Update(T entity) => _set.Update(entity);
    public virtual void Remove(T entity) => _set.Remove(entity);
}
