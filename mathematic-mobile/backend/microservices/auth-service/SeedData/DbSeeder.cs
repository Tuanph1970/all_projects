using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using AuthService.Domain.Entities;
using AuthService.Infrastructure.Persistence;

namespace AuthService.SeedData;

public class DbSeeder
{
    public static async Task Initialize(IServiceProvider serviceProvider)
    {
        using var context = new AuthDbContext(
            serviceProvider.GetRequiredService<DbContextOptions<AuthDbContext>>());

        // Check if there are any users
        if (context.Users.Any())
        {
            return; // Database has been seeded
        }

        // Create test users using the domain factory method
        var users = new[]
        {
            User.Create(
                username:     "admin",
                email:        "admin@mathsolver.com",
                passwordHash: BCrypt.Net.BCrypt.HashPassword("Admin123!"),
                fullName:     "Administrator",
                role:         "Admin"),

            User.Create(
                username:     "testuser",
                email:        "test@example.com",
                passwordHash: BCrypt.Net.BCrypt.HashPassword("Test123!"),
                fullName:     "Test User",
                role:         "User"),

            User.Create(
                username:     "student1",
                email:        "student1@school.com",
                passwordHash: BCrypt.Net.BCrypt.HashPassword("Student123!"),
                fullName:     "John Doe",
                role:         "User"),

            User.Create(
                username:     "student2",
                email:        "student2@school.com",
                passwordHash: BCrypt.Net.BCrypt.HashPassword("Student123!"),
                fullName:     "Jane Smith",
                role:         "User"),

            User.Create(
                username:     "teacher",
                email:        "teacher@school.com",
                passwordHash: BCrypt.Net.BCrypt.HashPassword("Teacher123!"),
                fullName:     "Mr. Johnson",
                role:         "Teacher"),
        };

        context.Users.AddRange(users);
        await context.SaveChangesAsync();

        Console.WriteLine("Auth Service database seeded successfully!");
        Console.WriteLine($"   Created {users.Length} test users");
        Console.WriteLine();
        Console.WriteLine("Test credentials:");
        Console.WriteLine("   Admin: admin / Admin123!");
        Console.WriteLine("   User: testuser / Test123!");
        Console.WriteLine("   Student: student1 / Student123!");
    }
}
