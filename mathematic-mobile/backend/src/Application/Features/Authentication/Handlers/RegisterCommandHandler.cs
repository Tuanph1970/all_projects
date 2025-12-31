using Application.Common.Exceptions;
using Application.Common.Interfaces;
using Application.DTOs;
using Application.Features.Authentication.Commands;
using Domain.Entities;
using Microsoft.Extensions.Logging;

namespace Application.Features.Authentication.Handlers;

public class RegisterCommandHandler : ICommandHandler<RegisterCommand, AuthResult>
{
    private readonly IUserRepository _userRepository;
    private readonly IPasswordHasher _passwordHasher;
    private readonly IJwtTokenGenerator _jwtTokenGenerator;
    private readonly IUnitOfWork _unitOfWork;
    private readonly ILogger<RegisterCommandHandler> _logger;

    public RegisterCommandHandler(
        IUserRepository userRepository,
        IPasswordHasher passwordHasher,
        IJwtTokenGenerator jwtTokenGenerator,
        IUnitOfWork unitOfWork,
        ILogger<RegisterCommandHandler> logger)
    {
        _userRepository = userRepository;
        _passwordHasher = passwordHasher;
        _jwtTokenGenerator = jwtTokenGenerator;
        _unitOfWork = unitOfWork;
        _logger = logger;
    }

    public async Task<AuthResult> Handle(RegisterCommand request, CancellationToken cancellationToken)
    {
        // Check if user already exists
        if (await _userRepository.ExistsByUsernameAsync(request.Username, cancellationToken))
        {
            _logger.LogWarning("Registration failed: Username {Username} already exists", request.Username);
            throw new ValidationException(new[]
            {
                new FluentValidation.Results.ValidationFailure("Username", "Username already exists")
            });
        }

        if (await _userRepository.ExistsByEmailAsync(request.Email, cancellationToken))
        {
            _logger.LogWarning("Registration failed: Email {Email} already exists", request.Email);
            throw new ValidationException(new[]
            {
                new FluentValidation.Results.ValidationFailure("Email", "Email already exists")
            });
        }

        // Hash password
        var passwordHash = _passwordHasher.HashPassword(request.Password);

        // Create user
        var user = new User(request.Username, request.Email, passwordHash);

        // Save to database
        await _userRepository.AddAsync(user, cancellationToken);
        await _unitOfWork.SaveChangesAsync(cancellationToken);

        // Generate token
        var token = _jwtTokenGenerator.GenerateToken(user);

        _logger.LogInformation("User {UserId} registered successfully", user.Id);

        return new AuthResult
        {
            Token = token,
            User = new UserDto
            {
                Id = user.Id,
                Username = user.Username,
                Email = user.Email,
                IsActive = user.IsActive,
                CreatedAt = user.CreatedAt
            }
        };
    }
}