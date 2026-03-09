using System;
using System.Linq;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using ProblemService.Data;
using ProblemService.Models;

namespace ProblemService.SeedData
{
    public class DbSeeder
    {
        public static async Task Initialize(IServiceProvider serviceProvider)
        {
            using var context = new ProblemDbContext(
                serviceProvider.GetRequiredService<DbContextOptions<ProblemDbContext>>());

            // Check if there are any problems
            if (context.Problems.Any())
            {
                return; // Database has been seeded
            }

            // Create test problems
            var problems = new[]
            {
                new Problem
                {
                    UserId = 1, // admin user
                    Title = "Solve quadratic equation",
                    Description = "Find the roots of x² - 5x + 6 = 0",
                    ExtractedText = "x² - 5x + 6 = 0",
                    Category = "Algebra",
                    Difficulty = "Medium",
                    Status = ProblemStatus.Solved,
                    CreatedAt = DateTime.UtcNow.AddDays(-5),
                    SolvedAt = DateTime.UtcNow.AddDays(-5).AddMinutes(2)
                },
                new Problem
                {
                    UserId = 2, // testuser
                    Title = "Calculate derivative",
                    Description = "Find the derivative of f(x) = 3x² + 2x - 1",
                    ExtractedText = "f(x) = 3x² + 2x - 1, find f'(x)",
                    Category = "Calculus",
                    Difficulty = "Easy",
                    Status = ProblemStatus.Solved,
                    CreatedAt = DateTime.UtcNow.AddDays(-3),
                    SolvedAt = DateTime.UtcNow.AddDays(-3).AddMinutes(1)
                },
                new Problem
                {
                    UserId = 3, // student1
                    Title = "System of linear equations",
                    Description = "Solve: 2x + y = 5, x - y = 1",
                    ExtractedText = "2x + y = 5\nx - y = 1",
                    Category = "Algebra",
                    Difficulty = "Medium",
                    Status = ProblemStatus.Processing,
                    CreatedAt = DateTime.UtcNow.AddDays(-1)
                },
                new Problem
                {
                    UserId = 3, // student1
                    Title = "Integral calculation",
                    Description = "Calculate ∫(2x + 3)dx",
                    ExtractedText = "∫(2x + 3)dx",
                    Category = "Calculus",
                    Difficulty = "Hard",
                    Status = ProblemStatus.Pending,
                    CreatedAt = DateTime.UtcNow
                },
                new Problem
                {
                    UserId = 4, // student2
                    Title = "Geometry problem",
                    Description = "Find the area of a triangle with sides 3, 4, 5",
                    ExtractedText = "Triangle sides: a=3, b=4, c=5. Find area.",
                    Category = "Geometry",
                    Difficulty = "Easy",
                    Status = ProblemStatus.Solved,
                    CreatedAt = DateTime.UtcNow.AddDays(-2),
                    SolvedAt = DateTime.UtcNow.AddDays(-2).AddMinutes(3)
                },
                new Problem
                {
                    UserId = 4, // student2
                    Title = "Trigonometric identity",
                    Description = "Prove: sin²(x) + cos²(x) = 1",
                    ExtractedText = "Prove sin²(x) + cos²(x) = 1",
                    Category = "Trigonometry",
                    Difficulty = "Medium",
                    Status = ProblemStatus.Failed,
                    CreatedAt = DateTime.UtcNow.AddDays(-4),
                    UpdatedAt = DateTime.UtcNow.AddDays(-4).AddMinutes(5)
                }
            };

            context.Problems.AddRange(problems);

            // Create problem history
            var histories = new[]
            {
                new ProblemHistory
                {
                    ProblemId = 1,
                    UserId = 1,
                    Action = "Created",
                    Details = "Problem submitted for solving",
                    CreatedAt = DateTime.UtcNow.AddDays(-5)
                },
                new ProblemHistory
                {
                    ProblemId = 1,
                    UserId = 1,
                    Action = "Processing",
                    Details = "OCR processing started",
                    CreatedAt = DateTime.UtcNow.AddDays(-5).AddMinutes(1)
                },
                new ProblemHistory
                {
                    ProblemId = 1,
                    UserId = 1,
                    Action = "Solved",
                    Details = "Solution generated successfully",
                    CreatedAt = DateTime.UtcNow.AddDays(-5).AddMinutes(2)
                },
                new ProblemHistory
                {
                    ProblemId = 2,
                    UserId = 2,
                    Action = "Created",
                    Details = "Problem submitted for solving",
                    CreatedAt = DateTime.UtcNow.AddDays(-3)
                },
                new ProblemHistory
                {
                    ProblemId = 2,
                    UserId = 2,
                    Action = "Solved",
                    Details = "Solution generated successfully",
                    CreatedAt = DateTime.UtcNow.AddDays(-3).AddMinutes(1)
                }
            };

            context.ProblemHistories.AddRange(histories);
            await context.SaveChangesAsync();

            Console.WriteLine("✅ Problem Service database seeded successfully!");
            Console.WriteLine($"   Created {problems.Length} test problems");
            Console.WriteLine($"   Created {histories.Length} problem history records");
            Console.WriteLine();
        }
    }
}
