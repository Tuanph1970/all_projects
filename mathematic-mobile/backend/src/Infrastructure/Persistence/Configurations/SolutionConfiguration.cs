using Domain.Entities;
using Domain.ValueObjects;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using System.Text.Json;

namespace Infrastructure.Persistence.Configurations;

public class SolutionConfiguration : IEntityTypeConfiguration<Solution>
{
    public void Configure(EntityTypeBuilder<Solution> builder)
    {
        builder.ToTable("Solutions");

        builder.HasKey(s => s.Id);

        builder.Property(s => s.Id)
            .ValueGeneratedNever();

        builder.Property(s => s.ProblemId)
            .IsRequired();

        builder.Property(s => s.Steps)
            .IsRequired()
            .HasConversion(
                v => JsonSerializer.Serialize(v, (JsonSerializerOptions?)null),
                v => JsonSerializer.Deserialize<List<SolutionStep>>(v, (JsonSerializerOptions?)null) ?? new List<SolutionStep>());

        builder.Property(s => s.Confidence)
            .IsRequired()
            .HasColumnType("decimal(5,4)");

        builder.Property(s => s.AdditionalNotes)
            .HasMaxLength(2000);

        builder.Property(s => s.CreatedAt)
            .IsRequired();

        builder.Property(s => s.UpdatedAt)
            .IsRequired(false);

        // Indexes
        builder.HasIndex(s => s.ProblemId)
            .IsUnique()
            .HasDatabaseName("IX_Solutions_ProblemId");

        builder.HasIndex(s => s.Confidence)
            .HasDatabaseName("IX_Solutions_Confidence");

        builder.HasIndex(s => s.CreatedAt)
            .HasDatabaseName("IX_Solutions_CreatedAt");

        // Relationships
        builder.HasOne(s => s.Problem)
            .WithOne(p => p.Solution)
            .HasForeignKey<Solution>(s => s.ProblemId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}