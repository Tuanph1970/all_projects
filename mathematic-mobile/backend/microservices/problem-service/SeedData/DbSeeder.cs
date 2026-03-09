using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using ProblemService.Domain.Entities;
using ProblemService.Infrastructure.Persistence;

namespace ProblemService.SeedData;

public class DbSeeder
{
    // Fixed Guids matching auth-service seed users
    private static readonly Guid AdminUserId    = new("00000000-0000-0000-0000-000000000001");
    private static readonly Guid TestUserId     = new("00000000-0000-0000-0000-000000000002");
    private static readonly Guid Student1UserId = new("00000000-0000-0000-0000-000000000003");
    private static readonly Guid Student2UserId = new("00000000-0000-0000-0000-000000000004");

    public static async Task Initialize(IServiceProvider serviceProvider)
    {
        using var context = new ProblemDbContext(
            serviceProvider.GetRequiredService<DbContextOptions<ProblemDbContext>>());

        if (context.Problems.Any()) return;

        var p1 = Problem.Create(AdminUserId, "Solve quadratic equation", "Find the roots of x² - 5x + 6 = 0", "Algebra", "Medium");
        p1.UpdateStatus(ProblemStatus.Completed, "x² - 5x + 6 = 0");

        var p2 = Problem.Create(TestUserId, "Calculate derivative", "Find the derivative of f(x) = 3x² + 2x - 1", "Calculus", "Easy");
        p2.UpdateStatus(ProblemStatus.Completed, "f(x) = 3x² + 2x - 1, find f'(x)");

        var p3 = Problem.Create(Student1UserId, "System of linear equations", "Solve: 2x + y = 5, x - y = 1", "Algebra", "Medium");
        p3.UpdateStatus(ProblemStatus.Processing);

        var p4 = Problem.Create(Student1UserId, "Integral calculation", "Calculate ∫(2x + 3)dx", "Calculus", "Hard");

        var p5 = Problem.Create(Student2UserId, "Geometry problem", "Find the area of a triangle with sides 3, 4, 5", "Geometry", "Easy");
        p5.UpdateStatus(ProblemStatus.Completed, "Triangle sides: a=3, b=4, c=5. Find area.");

        var p6 = Problem.Create(Student2UserId, "Trigonometric identity", "Prove: sin²(x) + cos²(x) = 1", "Trigonometry", "Medium");
        p6.UpdateStatus(ProblemStatus.Failed);

        var problems = new[] { p1, p2, p3, p4, p5, p6 };
        context.Problems.AddRange(problems);
        await context.SaveChangesAsync();

        var histories = new[]
        {
            ProblemHistory.Create(p1.Id, AdminUserId, "Created", "Problem submitted for solving"),
            ProblemHistory.Create(p1.Id, AdminUserId, "Processing", "OCR processing started"),
            ProblemHistory.Create(p1.Id, AdminUserId, "Completed", "Solution generated successfully"),
            ProblemHistory.Create(p2.Id, TestUserId, "Created", "Problem submitted for solving"),
            ProblemHistory.Create(p2.Id, TestUserId, "Completed", "Solution generated successfully"),
        };

        context.ProblemHistories.AddRange(histories);
        await context.SaveChangesAsync();

        Console.WriteLine("✅ Problem Service database seeded successfully!");
        Console.WriteLine($"   Created {problems.Length} test problems");
        Console.WriteLine($"   Created {histories.Length} problem history records");
    }
}
