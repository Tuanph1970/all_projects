using Domain.Entities;
using Domain.Enums;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Infrastructure.Persistence.Configurations;

public class ProblemConfiguration : IEntityTypeConfiguration<Problem>
{
    public void Configure(EntityTypeBuilder<Problem> builder)
    {
        builder.ToTable("Problems");

        builder.HasKey(p => p.Id);

        builder.Property(p => p.Id)
            .ValueGeneratedNever();

        builder.Property(p => p.UserId)
            .IsRequired();

        builder.Property(p => p.ImageUrl)
            .IsRequired()
            .HasMaxLength(500);

        builder.Property(p => p.Category)
            .IsRequired()
            .HasMaxLength(100);

        builder.Property(p => p.Status)
            .IsRequired()
            .HasConversion<int>()
            .HasDefaultValue(ProblemStatus.Pending);

        builder.Property(p => p.Description)
            .HasMaxLength(1000);

        builder.Property(p => p.CreatedAt)
            .IsRequired();

        builder.Property(p => p.UpdatedAt)
            .IsRequired(false);

        // Indexes
        builder.HasIndex(p => p.UserId)
            .HasDatabaseName("IX_Problems_UserId");

        builder.HasIndex(p => p.Status)
            .HasDatabaseName("IX_Problems_Status");

        builder.HasIndex(p => p.Category)
            .HasDatabaseName("IX_Problems_Category");

        builder.HasIndex(p => p.CreatedAt)
            .HasDatabaseName("IX_Problems_CreatedAt");

        // Relationships
        builder.HasOne(p => p.User)
            .WithMany(u => u.Problems)
            .HasForeignKey(p => p.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        builder.HasOne(p => p.Solution)
            .WithOne(s => s.Problem)
            .HasForeignKey<Solution>(s => s.ProblemId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}