using Domain.Entities;

namespace Application.Common.Interfaces;

public interface IJwtTokenGenerator
{
    string GenerateToken(User user);
    Task<string> GenerateRefreshTokenAsync(User user);
    bool ValidateToken(string token);
    Guid? GetUserIdFromToken(string token);
}