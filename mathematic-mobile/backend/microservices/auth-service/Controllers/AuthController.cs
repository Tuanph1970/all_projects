using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;
using AuthService.Application.Features.Authentication.Commands;
using AuthService.Application.Features.Authentication.Queries;

namespace AuthService.Controllers;

[ApiController]
[Route("api/v1/auth")]
public class AuthController : ControllerBase
{
    private readonly ISender _sender;
    private readonly ILogger<AuthController> _logger;

    public AuthController(ISender sender, ILogger<AuthController> logger)
    { _sender = sender; _logger = logger; }

    private Guid? GetUserId()
    {
        var claim = User.FindFirst(ClaimTypes.NameIdentifier) ?? User.FindFirst("sub");
        return claim is not null && Guid.TryParse(claim.Value, out var id) ? id : null;
    }

    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest req, CancellationToken ct)
    {
        var result = await _sender.Send(new RegisterCommand(req.Username, req.Email, req.Password, req.FullName), ct);
        return Ok(new { success = true, message = "Registration successful", data = result });
    }

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest req, CancellationToken ct)
    {
        var result = await _sender.Send(new LoginCommand(req.UsernameOrEmail, req.Password), ct);
        return Ok(new { success = true, message = "Login successful", data = result });
    }

    [HttpPost("refresh")]
    public async Task<IActionResult> RefreshToken([FromBody] RefreshTokenRequest req, CancellationToken ct)
    {
        var result = await _sender.Send(new RefreshTokenCommand(req.RefreshToken), ct);
        return Ok(new { success = true, message = "Token refreshed", data = result });
    }

    [HttpPost("validate")]
    public async Task<IActionResult> ValidateToken([FromBody] ValidateTokenRequest req, CancellationToken ct)
    {
        var result = await _sender.Send(new ValidateTokenQuery(req.Token), ct);
        return Ok(new { success = result.IsValid, data = result });
    }

    [Authorize]
    [HttpGet("me")]
    public async Task<IActionResult> GetCurrentUser(CancellationToken ct)
    {
        var userId = GetUserId();
        if (userId is null) return Unauthorized(new { success = false, message = "Invalid token" });
        var user = await _sender.Send(new GetCurrentUserQuery(userId.Value), ct);
        return Ok(new { success = true, data = user });
    }

    [Authorize]
    [HttpPut("profile")]
    public async Task<IActionResult> UpdateProfile([FromBody] UpdateProfileRequest req, CancellationToken ct)
    {
        var userId = GetUserId();
        if (userId is null) return Unauthorized(new { success = false, message = "Invalid token" });
        await _sender.Send(new UpdateProfileCommand(userId.Value, req.FullName, req.Email), ct);
        return Ok(new { success = true, message = "Profile updated successfully" });
    }

    [Authorize]
    [HttpPost("change-password")]
    public async Task<IActionResult> ChangePassword([FromBody] ChangePasswordRequest req, CancellationToken ct)
    {
        var userId = GetUserId();
        if (userId is null) return Unauthorized(new { success = false, message = "Invalid token" });
        await _sender.Send(new ChangePasswordCommand(userId.Value, req.CurrentPassword, req.NewPassword), ct);
        return Ok(new { success = true, message = "Password changed successfully" });
    }
}

[ApiController]
[Route("api/v1/users")]
public class UsersController : ControllerBase
{
    private readonly ISender _sender;
    public UsersController(ISender sender) => _sender = sender;

    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetUser(Guid id, CancellationToken ct)
    {
        var user = await _sender.Send(new GetUserByIdQuery(id), ct);
        return Ok(new { success = true, data = user });
    }
}

// Presentation-layer request records (kept here for the external API contract)
public record RegisterRequest(string Username, string Email, string Password, string? FullName);
public record LoginRequest(string UsernameOrEmail, string Password);
public record RefreshTokenRequest(string RefreshToken);
public record ValidateTokenRequest(string Token);
public record UpdateProfileRequest(string? FullName, string? Email);
public record ChangePasswordRequest(string CurrentPassword, string NewPassword);
