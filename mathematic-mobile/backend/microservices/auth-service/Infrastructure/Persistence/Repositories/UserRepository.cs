using Microsoft.EntityFrameworkCore;
using AuthService.Application.Common.Interfaces;
using AuthService.Domain.Entities;

namespace AuthService.Infrastructure.Persistence.Repositories;

public class UserRepository : Repository<User>, IUserRepository
{
    public UserRepository(AuthDbContext db) : base(db) { }

    public Task<User?> GetByUsernameAsync(string username, CancellationToken ct = default)
        => _set.FirstOrDefaultAsync(u => u.Username == username, ct);

    public Task<User?> GetByEmailAsync(string email, CancellationToken ct = default)
        => _set.FirstOrDefaultAsync(u => u.Email == email, ct);

    public Task<User?> GetByUsernameOrEmailAsync(string identifier, CancellationToken ct = default)
        => _set.FirstOrDefaultAsync(u => u.Username == identifier || u.Email == identifier, ct);

    public Task<bool> ExistsByUsernameAsync(string username, CancellationToken ct = default)
        => _set.AnyAsync(u => u.Username == username, ct);

    public Task<bool> ExistsByEmailAsync(string email, CancellationToken ct = default)
        => _set.AnyAsync(u => u.Email == email, ct);
}
