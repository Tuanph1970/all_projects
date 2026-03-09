namespace AuthService.Application.DTOs;

public record AuthResultDto(
    Guid UserId,
    string Username,
    string Email,
    string? FullName,
    string Role,
    string AccessToken,
    string RefreshToken,
    DateTime ExpiresAt
);
