namespace Application.DTOs;

public class AuthResult
{
    public string Token { get; set; } = string.Empty;
    public UserDto User { get; set; } = null!;
}