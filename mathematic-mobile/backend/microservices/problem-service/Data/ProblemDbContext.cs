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
            entity.Property(e => e.ExtractedText).HasColumnType("text");
            entity.Property(e => e.Category).HasMaxLength(50).HasDefaultValue("General");
            entity.Property(e => e.Difficulty).HasMaxLength(20).HasDefaultValue("Medium");
            entity.Property(e => e.Status).HasConversion<int>();

            // Indexes for performance
            entity.HasIndex(e => e.UserId).HasDatabaseName("IX_Problems_UserId");
            entity.HasIndex(e => e.Status).HasDatabaseName("IX_Problems_Status");
            entity.HasIndex(e => e.Category).HasDatabaseName("IX_Problems_Category");
            entity.HasIndex(e => e.Difficulty).HasDatabaseName("IX_Problems_Difficulty");
            entity.HasIndex(e => e.CreatedAt).HasDatabaseName("IX_Problems_CreatedAt");
            entity.HasIndex(e => e.SolvedAt).HasDatabaseName("IX_Problems_SolvedAt");
        });

        modelBuilder.Entity<ProblemHistory>(entity =>
        {
            entity.ToTable("ProblemHistories");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Action).IsRequired().HasMaxLength(50);
            entity.Property(e => e.Details).HasMaxLength(1000);

            // Indexes for performance
            entity.HasIndex(e => e.ProblemId).HasDatabaseName("IX_ProblemHistories_ProblemId");
            entity.HasIndex(e => e.UserId).HasDatabaseName("IX_ProblemHistories_UserId");
            entity.HasIndex(e => e.CreatedAt).HasDatabaseName("IX_ProblemHistories_CreatedAt");
        });
    }
}
