namespace AuthService.Application.DTOs;

public record UserDto(
    Guid Id,
    string Username,
    string Email,
    string? FullName,
    string Role,
    bool IsActive,
    DateTime CreatedAt,
    DateTime? LastLoginAt
);
