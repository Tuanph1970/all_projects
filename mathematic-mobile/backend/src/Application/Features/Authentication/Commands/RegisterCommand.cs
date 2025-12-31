using Application.Common.Interfaces;
using Application.DTOs;

namespace Application.Features.Authentication.Commands;

public class RegisterCommand : ICommand<AuthResult>
{
    public string Username { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public string ConfirmPassword { get; set; } = string.Empty;
}