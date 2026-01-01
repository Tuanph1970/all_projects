using Microsoft.EntityFrameworkCore;
using ProblemService.Models;

namespace ProblemService.Data;

public class ProblemDbContext : DbContext
{
    public ProblemDbContext(DbContextOptions<ProblemDbContext> options) : base(options)
    {
    }

    public DbSet<Problem> Problems { get; set; } = null!;
    public DbSet<ProblemHistory> ProblemHistories { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Problem>(entity =>
        {
            entity.ToTable("Problems");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Title).IsRequired().HasMaxLength(200);
            entity.Property(e => e.Description).HasMaxLength(2000);
            entity.Property(e => e.ImagePath).HasMaxLength(500);
            entity.Property(e => e.Category).HasMaxLength(50).HasDefaultValue("General");
            entity.Property(e => e.Difficulty).HasMaxLength(20).HasDefaultValue("Medium");
            entity.Property(e => e.Status).HasConversion<int>();

            entity.HasIndex(e => e.UserId);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.CreatedAt);
        });

        modelBuilder.Entity<ProblemHistory>(entity =>
        {
            entity.ToTable("ProblemHistories");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Action).IsRequired().HasMaxLength(50);
            entity.Property(e => e.Details).HasMaxLength(1000);

            entity.HasIndex(e => e.ProblemId);
            entity.HasIndex(e => e.UserId);
        });
    }
}
