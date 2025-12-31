using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;

namespace Presentation.Extensions;

public static class ClaimsPrincipalExtensions
{
    public static Guid GetUserId(this ClaimsPrincipal user)
    {
        var userIdClaim = user.Claims.FirstOrDefault(c => c.Type == JwtRegisteredClaimNames.Sub);
        
        if (userIdClaim != null && Guid.TryParse(userIdClaim.Value, out var userId))
        {
            return userId;
        }
        
        throw new UnauthorizedAccessException("User ID not found in token");
    }

    public static string GetUsername(this ClaimsPrincipal user)
    {
        var usernameClaim = user.Claims.FirstOrDefault(c => c.Type == JwtRegisteredClaimNames.UniqueName);
        return usernameClaim?.Value ?? throw new UnauthorizedAccessException("Username not found in token");
    }

    public static string GetEmail(this ClaimsPrincipal user)
    {
        var emailClaim = user.Claims.FirstOrDefault(c => c.Type == JwtRegisteredClaimNames.Email);
        return emailClaim?.Value ?? throw new UnauthorizedAccessException("Email not found in token");
    }

    public static bool IsActive(this ClaimsPrincipal user)
    {
        var activeClaim = user.Claims.FirstOrDefault(c => c.Type == "active");
        return activeClaim != null && bool.TryParse(activeClaim.Value, out var isActive) && isActive;
    }
}