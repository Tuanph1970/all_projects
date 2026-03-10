using AuthService.Application.Features.Authentication.Commands;
using FluentAssertions;
using FluentValidation.TestHelper;

namespace AuthService.Tests.Application.Validators;

public class LoginCommandValidatorTests
{
    private readonly LoginCommandValidator _validator = new();

    [Fact]
    public void Validate_ValidCredentials_PassesWithNoErrors()
    {
        var cmd = new LoginCommand("johndoe", "securePass1");
        var result = _validator.TestValidate(cmd);
        result.ShouldNotHaveAnyValidationErrors();
    }

    [Fact]
    public void Validate_ValidEmailCredentials_PassesWithNoErrors()
    {
        var cmd = new LoginCommand("john@example.com", "securePass1");
        var result = _validator.TestValidate(cmd);
        result.ShouldNotHaveAnyValidationErrors();
    }

    [Theory]
    [InlineData("")]
    [InlineData("  ")]
    public void Validate_EmptyUsernameOrEmail_HasValidationError(string identifier)
    {
        var cmd = new LoginCommand(identifier, "pass123");
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.UsernameOrEmail);
    }

    [Theory]
    [InlineData("")]
    [InlineData("  ")]
    public void Validate_EmptyPassword_HasValidationError(string password)
    {
        var cmd = new LoginCommand("user", password);
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Password);
    }

    [Fact]
    public void Validate_PasswordTooShort_HasValidationError()
    {
        var cmd = new LoginCommand("user", "abc");
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Password);
    }

    [Fact]
    public void Validate_PasswordAtMinLength_Passes()
    {
        var cmd = new LoginCommand("user", "abcdef");
        var result = _validator.TestValidate(cmd);
        result.ShouldNotHaveValidationErrorFor(x => x.Password);
    }
}
