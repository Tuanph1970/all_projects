using Microsoft.EntityFrameworkCore;
using ProblemService.Domain.Entities;

namespace ProblemService.Infrastructure.Persistence;

public class ProblemDbContext : DbContext
{
    public ProblemDbContext(DbContextOptions<ProblemDbContext> options) : base(options) { }

    public DbSet<Problem> Problems { get; set; } = null!;
    public DbSet<ProblemHistory> ProblemHistories { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(ProblemDbContext).Assembly);
    }
}
