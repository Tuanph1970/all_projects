using System;
using System.Linq;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using AuthService.Data;
using AuthService.Models;
using BCrypt.Net;

namespace AuthService.SeedData
{
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

            // Create test users
            var users = new[]
            {
                new User
                {
                    Username = "admin",
                    Email = "admin@mathsolver.com",
                    PasswordHash = BCrypt.Net.BCrypt.HashPassword("Admin123!"),
                    FullName = "Administrator",
                    Role = "Admin",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow,
                    LastLoginAt = DateTime.UtcNow
                },
                new User
                {
                    Username = "testuser",
                    Email = "test@example.com",
                    PasswordHash = BCrypt.Net.BCrypt.HashPassword("Test123!"),
                    FullName = "Test User",
                    Role = "User",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow
                },
                new User
                {
                    Username = "student1",
                    Email = "student1@school.com",
                    PasswordHash = BCrypt.Net.BCrypt.HashPassword("Student123!"),
                    FullName = "John Doe",
                    Role = "User",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow
                },
                new User
                {
                    Username = "student2",
                    Email = "student2@school.com",
                    PasswordHash = BCrypt.Net.BCrypt.HashPassword("Student123!"),
                    FullName = "Jane Smith",
                    Role = "User",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow
                },
                new User
                {
                    Username = "teacher",
                    Email = "teacher@school.com",
                    PasswordHash = BCrypt.Net.BCrypt.HashPassword("Teacher123!"),
                    FullName = "Mr. Johnson",
                    Role = "Teacher",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow
                }
            };

            context.Users.AddRange(users);
            await context.SaveChangesAsync();

            Console.WriteLine("✅ Auth Service database seeded successfully!");
            Console.WriteLine($"   Created {users.Length} test users");
            Console.WriteLine();
            Console.WriteLine("Test credentials:");
            Console.WriteLine("   Admin: admin / Admin123!");
            Console.WriteLine("   User: testuser / Test123!");
            Console.WriteLine("   Student: student1 / Student123!");
        }
    }
}
