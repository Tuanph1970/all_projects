using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ProblemService.Domain.Entities;

namespace ProblemService.Infrastructure.Persistence.Configurations;

public class ProblemConfiguration : IEntityTypeConfiguration<Problem>
{
    public void Configure(EntityTypeBuilder<Problem> builder)
    {
        builder.ToTable("Problems");
        builder.HasKey(e => e.Id);
        builder.Property(e => e.Id).HasColumnType("char(36)");

        builder.Property(e => e.UserId).HasColumnType("char(36)");
        builder.Property(e => e.Title).IsRequired().HasMaxLength(200);
        builder.Property(e => e.Description).HasMaxLength(2000);
        builder.Property(e => e.ImagePath).HasMaxLength(500);
        builder.Property(e => e.ExtractedText).HasColumnType("text");
        builder.Property(e => e.Category).HasMaxLength(50).HasDefaultValue("General");
        builder.Property(e => e.Difficulty).HasMaxLength(20).HasDefaultValue("Medium");
        builder.Property(e => e.Status).HasConversion<int>();

        builder.Ignore(e => e.DomainEvents);

        builder.HasIndex(e => e.UserId).HasDatabaseName("IX_Problems_UserId");
        builder.HasIndex(e => e.Status).HasDatabaseName("IX_Problems_Status");
        builder.HasIndex(e => e.Category).HasDatabaseName("IX_Problems_Category");
        builder.HasIndex(e => e.CreatedAt).HasDatabaseName("IX_Problems_CreatedAt");
    }
}
