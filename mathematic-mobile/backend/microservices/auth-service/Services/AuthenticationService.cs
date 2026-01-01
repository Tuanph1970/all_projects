using Microsoft.EntityFrameworkCore;
using AuthService.Data;
using AuthService.DTOs;
using AuthService.Models;

namespace AuthService.Services;

public interface IAuthenticationService
{
    Task<(bool Success, string Message, AuthResponse? Response)> RegisterAsync(RegisterRequest request);
    Task<(bool Success, string Message, AuthResponse? Response)> LoginAsync(LoginRequest request);
    Task<(bool Success, string Message, AuthResponse? Response)> RefreshTokenAsync(string refreshToken);
    Task<UserResponse?> GetUserByIdAsync(int userId);
    Task<(bool Success, string Message)> UpdateProfileAsync(int userId, UpdateProfileRequest request);
    Task<(bool Success, string Message)> ChangePasswordAsync(int userId, ChangePasswordRequest request);
    Task<TokenValidationResponse> ValidateTokenAsync(string token);
}

public class AuthenticationService : IAuthenticationService
{
    private readonly AuthDbContext _context;
    private readonly IJwtService _jwtService;
    private readonly ILogger<AuthenticationService> _logger;

    public AuthenticationService(
        AuthDbContext context,
        IJwtService jwtService,
        ILogger<AuthenticationService> logger)
    {
        _context = context;
        _jwtService = jwtService;
        _logger = logger;
    }

    public async Task<(bool Success, string Message, AuthResponse? Response)> RegisterAsync(RegisterRequest request)
    {
        try
        {
            // Check if username or email already exists
            if (await _context.Users.AnyAsync(u => u.Username == request.Username))
            {
                return (false, "Username already exists", null);
            }

            if (await _context.Users.AnyAsync(u => u.Email == request.Email))
            {
                return (false, "Email already exists", null);
            }

            var user = new User
            {
                Username = request.Username,
                Email = request.Email,
                PasswordHash = BCrypt.Net.BCrypt.HashPassword(request.Password),
                FullName = request.FullName,
                Role = "User",
                IsActive = true,
                CreatedAt = DateTime.UtcNow
            };

            _context.Users.Add(user);
            await _context.SaveChangesAsync();

            var accessToken = _jwtService.GenerateAccessToken(user);
            var refreshToken = _jwtService.GenerateRefreshToken();

            _logger.LogInformation("User registered successfully: {Username}", user.Username);

            return (true, "Registration successful", new AuthResponse(
                user.Id,
                user.Username,
                user.Email,
                user.FullName,
                user.Role,
                accessToken,
                refreshToken,
                DateTime.UtcNow.AddHours(1)
            ));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error during registration for {Username}", request.Username);
            return (false, "Registration failed. Please try again.", null);
        }
    }

    public async Task<(bool Success, string Message, AuthResponse? Response)> LoginAsync(LoginRequest request)
    {
        try
        {
            var user = await _context.Users.FirstOrDefaultAsync(u =>
                u.Username == request.UsernameOrEmail || u.Email == request.UsernameOrEmail);

            if (user == null)
            {
                return (false, "Invalid username or password", null);
            }

            if (!user.IsActive)
            {
                return (false, "Account is deactivated", null);
            }

            if (!BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            {
                return (false, "Invalid username or password", null);
            }

            // Update last login
            user.LastLoginAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();

            var accessToken = _jwtService.GenerateAccessToken(user);
            var refreshToken = _jwtService.GenerateRefreshToken();

            _logger.LogInformation("User logged in: {Username}", user.Username);

            return (true, "Login successful", new AuthResponse(
                user.Id,
                user.Username,
                user.Email,
                user.FullName,
                user.Role,
                accessToken,
                refreshToken,
                DateTime.UtcNow.AddHours(1)
            ));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error during login for {UsernameOrEmail}", request.UsernameOrEmail);
            return (false, "Login failed. Please try again.", null);
        }
    }

    public async Task<(bool Success, string Message, AuthResponse? Response)> RefreshTokenAsync(string refreshToken)
    {
        // In production, validate refresh token from database/cache
        // For now, this is a simplified implementation
        return (false, "Refresh token validation not implemented", null);
    }

    public async Task<UserResponse?> GetUserByIdAsync(int userId)
    {
        var user = await _context.Users.FindAsync(userId);
        if (user == null) return null;

        return new UserResponse(
            user.Id,
            user.Username,
            user.Email,
            user.FullName,
            user.Role,
            user.IsActive,
            user.CreatedAt,
            user.LastLoginAt
        );
    }

    public async Task<(bool Success, string Message)> UpdateProfileAsync(int userId, UpdateProfileRequest request)
    {
        var user = await _context.Users.FindAsync(userId);
        if (user == null)
        {
            return (false, "User not found");
        }

        if (!string.IsNullOrEmpty(request.Email) && request.Email != user.Email)
        {
            if (await _context.Users.AnyAsync(u => u.Email == request.Email && u.Id != userId))
            {
                return (false, "Email already in use");
            }
            user.Email = request.Email;
        }

        if (request.FullName != null)
        {
            user.FullName = request.FullName;
        }

        user.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return (true, "Profile updated successfully");
    }

    public async Task<(bool Success, string Message)> ChangePasswordAsync(int userId, ChangePasswordRequest request)
    {
        var user = await _context.Users.FindAsync(userId);
        if (user == null)
        {
            return (false, "User not found");
        }

        if (!BCrypt.Net.BCrypt.Verify(request.CurrentPassword, user.PasswordHash))
        {
            return (false, "Current password is incorrect");
        }

        user.PasswordHash = BCrypt.Net.BCrypt.HashPassword(request.NewPassword);
        user.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return (true, "Password changed successfully");
    }

    public async Task<TokenValidationResponse> ValidateTokenAsync(string token)
    {
        var userId = _jwtService.GetUserIdFromToken(token);
        if (userId == null)
        {
            return new TokenValidationResponse(false, null, null, null, "Invalid or expired token");
        }

        var user = await _context.Users.FindAsync(userId.Value);
        if (user == null || !user.IsActive)
        {
            return new TokenValidationResponse(false, null, null, null, "User not found or inactive");
        }

        return new TokenValidationResponse(true, user.Id, user.Username, user.Role, "Token is valid");
    }
}
