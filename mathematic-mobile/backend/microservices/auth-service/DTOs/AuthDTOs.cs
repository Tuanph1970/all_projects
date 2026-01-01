using System.ComponentModel.DataAnnotations;

namespace AuthService.DTOs;

public record RegisterRequest(
    [Required][StringLength(50, MinimumLength = 3)] string Username,
    [Required][EmailAddress] string Email,
    [Required][StringLength(100, MinimumLength = 6)] string Password,
    string? FullName
);

public record LoginRequest(
    [Required] string UsernameOrEmail,
    [Required] string Password
);

public record RefreshTokenRequest(
    [Required] string RefreshToken
);

public record AuthResponse(
    int UserId,
    string Username,
    string Email,
    string? FullName,
    string Role,
    string AccessToken,
    string RefreshToken,
    DateTime ExpiresAt
);

public record UserResponse(
    int Id,
    string Username,
    string Email,
    string? FullName,
    string Role,
    bool IsActive,
    DateTime CreatedAt,
    DateTime? LastLoginAt
);

public record UpdateProfileRequest(
    string? FullName,
    string? Email
);

public record ChangePasswordRequest(
    [Required] string CurrentPassword,
    [Required][StringLength(100, MinimumLength = 6)] string NewPassword
);

public record ValidateTokenRequest(
    [Required] string Token
);

public record TokenValidationResponse(
    bool IsValid,
    int? UserId,
    string? Username,
    string? Role,
    string? Message
);
