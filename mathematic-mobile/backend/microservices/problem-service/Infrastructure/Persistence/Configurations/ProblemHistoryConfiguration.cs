using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ProblemService.Domain.Entities;

namespace ProblemService.Infrastructure.Persistence.Configurations;

public class ProblemHistoryConfiguration : IEntityTypeConfiguration<ProblemHistory>
{
    public void Configure(EntityTypeBuilder<ProblemHistory> builder)
    {
        builder.ToTable("ProblemHistories");
        builder.HasKey(e => e.Id);
        builder.Property(e => e.Id).HasColumnType("char(36)");
        builder.Property(e => e.ProblemId).HasColumnType("char(36)");
        builder.Property(e => e.UserId).HasColumnType("char(36)");
        builder.Property(e => e.Action).IsRequired().HasMaxLength(50);
        builder.Property(e => e.Details).HasMaxLength(1000);

        builder.Ignore(e => e.DomainEvents);

        builder.HasIndex(e => e.ProblemId).HasDatabaseName("IX_ProblemHistories_ProblemId");
        builder.HasIndex(e => e.UserId).HasDatabaseName("IX_ProblemHistories_UserId");
        builder.HasIndex(e => e.CreatedAt).HasDatabaseName("IX_ProblemHistories_CreatedAt");
    }
}
