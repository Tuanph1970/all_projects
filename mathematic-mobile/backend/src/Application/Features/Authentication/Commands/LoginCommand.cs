using Application.Common.Interfaces;
using Application.DTOs;

namespace Application.Features.Authentication.Commands;

public class LoginCommand : ICommand<AuthResult>
{
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
}