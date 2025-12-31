using Application.Common.Exceptions;
using Application.Common.Interfaces;
using Application.DTOs;
using Application.Features.Authentication.Commands;
using Microsoft.Extensions.Logging;

namespace Application.Features.Authentication.Handlers;

public class LoginCommandHandler : ICommandHandler<LoginCommand, AuthResult>
{
    private readonly IUserRepository _userRepository;
    private readonly IPasswordHasher _passwordHasher;
    private readonly IJwtTokenGenerator _jwtTokenGenerator;
    private readonly IUnitOfWork _unitOfWork;
    private readonly ILogger<LoginCommandHandler> _logger;

    public LoginCommandHandler(
        IUserRepository userRepository,
        IPasswordHasher passwordHasher,
        IJwtTokenGenerator jwtTokenGenerator,
        IUnitOfWork unitOfWork,
        ILogger<LoginCommandHandler> logger)
    {
        _userRepository = userRepository;
        _passwordHasher = passwordHasher;
        _jwtTokenGenerator = jwtTokenGenerator;
        _unitOfWork = unitOfWork;
        _logger = logger;
    }

    public async Task<AuthResult> Handle(LoginCommand request, CancellationToken cancellationToken)
    {
        var user = await _userRepository.GetByUsernameAsync(request.Username, cancellationToken);

        if (user == null || !_passwordHasher.VerifyPassword(request.Password, user.PasswordHash))
        {
            _logger.LogWarning("Login failed for username: {Username}", request.Username);
            throw new UnauthorizedException("Invalid credentials");
        }

        if (!user.IsActive)
        {
            _logger.LogWarning("Login failed: User {Username} is deactivated", request.Username);
            throw new UnauthorizedException("User account is deactivated");
        }

        // Update last login
        user.UpdateLastLogin();
        await _userRepository.UpdateAsync(user, cancellationToken);
        await _unitOfWork.SaveChangesAsync(cancellationToken);

        // Generate token
        var token = _jwtTokenGenerator.GenerateToken(user);

        _logger.LogInformation("User {UserId} logged in successfully", user.Id);

        return new AuthResult
        {
            Token = token,
            User = new UserDto
            {
                Id = user.Id,
                Username = user.Username,
                Email = user.Email,
                IsActive = user.IsActive,
                CreatedAt = user.CreatedAt,
                LastLoginAt = user.LastLoginAt
            }
        };
    }
}