using AuthService.Application.Features.Authentication.Commands;
using FluentAssertions;
using FluentValidation.TestHelper;

namespace AuthService.Tests.Application.Validators;

public class RegisterCommandValidatorTests
{
    private readonly RegisterCommandValidator _validator = new();

    [Fact]
    public void Validate_ValidCommand_PassesWithNoErrors()
    {
        var cmd = new RegisterCommand("johndoe", "john@example.com", "securePass1", "John Doe");
        var result = _validator.TestValidate(cmd);
        result.ShouldNotHaveAnyValidationErrors();
    }

    [Theory]
    [InlineData("")]
    [InlineData("  ")]
    public void Validate_EmptyUsername_HasValidationError(string username)
    {
        var cmd = new RegisterCommand(username, "email@test.com", "pass123", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Username);
    }

    [Fact]
    public void Validate_UsernameTooShort_HasValidationError()
    {
        var cmd = new RegisterCommand("ab", "email@test.com", "pass123", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Username);
    }

    [Fact]
    public void Validate_UsernameTooLong_HasValidationError()
    {
        var longUsername = new string('a', 51);
        var cmd = new RegisterCommand(longUsername, "email@test.com", "pass123", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Username);
    }

    [Fact]
    public void Validate_UsernameAtMinLength_Passes()
    {
        var cmd = new RegisterCommand("abc", "email@test.com", "pass123", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldNotHaveValidationErrorFor(x => x.Username);
    }

    [Fact]
    public void Validate_UsernameAtMaxLength_Passes()
    {
        var maxUsername = new string('a', 50);
        var cmd = new RegisterCommand(maxUsername, "email@test.com", "pass123", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldNotHaveValidationErrorFor(x => x.Username);
    }

    [Theory]
    [InlineData("")]
    [InlineData("  ")]
    public void Validate_EmptyEmail_HasValidationError(string email)
    {
        var cmd = new RegisterCommand("validuser", email, "pass123", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Email);
    }

    [Theory]
    [InlineData("notanemail")]
    [InlineData("missing@domain")]
    [InlineData("@nodomain.com")]
    public void Validate_InvalidEmailFormat_HasValidationError(string email)
    {
        var cmd = new RegisterCommand("validuser", email, "pass123", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Email);
    }

    [Theory]
    [InlineData("")]
    [InlineData("  ")]
    public void Validate_EmptyPassword_HasValidationError(string password)
    {
        var cmd = new RegisterCommand("validuser", "email@test.com", password, null);
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Password);
    }

    [Fact]
    public void Validate_PasswordTooShort_HasValidationError()
    {
        var cmd = new RegisterCommand("validuser", "email@test.com", "abc", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Password);
    }

    [Fact]
    public void Validate_PasswordAtMinLength_Passes()
    {
        var cmd = new RegisterCommand("validuser", "email@test.com", "abcdef", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldNotHaveValidationErrorFor(x => x.Password);
    }

    [Fact]
    public void Validate_PasswordTooLong_HasValidationError()
    {
        var longPwd = new string('a', 101);
        var cmd = new RegisterCommand("validuser", "email@test.com", longPwd, null);
        var result = _validator.TestValidate(cmd);
        result.ShouldHaveValidationErrorFor(x => x.Password);
    }

    [Fact]
    public void Validate_NullFullName_IsAllowed()
    {
        var cmd = new RegisterCommand("validuser", "email@test.com", "pass123", null);
        var result = _validator.TestValidate(cmd);
        result.ShouldNotHaveAnyValidationErrors();
    }
}
