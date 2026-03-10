using AuthService.Domain.Entities;
using FluentAssertions;

namespace AuthService.Tests.Domain;

public class UserEntityTests
{
    // ── Create ────────────────────────────────────────────────────

    [Fact]
    public void Create_ValidData_SetsPropertiesCorrectly()
    {
        var user = User.Create("johndoe", "john@example.com", "hashed_pwd", "John Doe");

        user.Username.Should().Be("johndoe");
        user.Email.Should().Be("john@example.com");
        user.PasswordHash.Should().Be("hashed_pwd");
        user.FullName.Should().Be("John Doe");
        user.Role.Should().Be("User");
        user.IsActive.Should().BeTrue();
        user.LastLoginAt.Should().BeNull();
        user.Id.Should().NotBe(Guid.Empty);
    }

    [Fact]
    public void Create_WithCustomRole_SetsRole()
    {
        var user = User.Create("admin", "admin@example.com", "hash", null, "Admin");
        user.Role.Should().Be("Admin");
    }

    [Fact]
    public void Create_WithNullFullName_SetsNullFullName()
    {
        var user = User.Create("janedoe", "jane@example.com", "hash");
        user.FullName.Should().BeNull();
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Create_WithNullOrWhitespaceUsername_ThrowsArgumentException(string? username)
    {
        var act = () => User.Create(username!, "email@test.com", "hash");
        act.Should().Throw<ArgumentException>();
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Create_WithNullOrWhitespaceEmail_ThrowsArgumentException(string? email)
    {
        var act = () => User.Create("user", email!, "hash");
        act.Should().Throw<ArgumentException>();
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Create_WithNullOrWhitespacePasswordHash_ThrowsArgumentException(string? hash)
    {
        var act = () => User.Create("user", "email@test.com", hash!);
        act.Should().Throw<ArgumentException>();
    }

    // ── RecordLogin ───────────────────────────────────────────────

    [Fact]
    public void RecordLogin_SetsLastLoginAtToNow()
    {
        var user = User.Create("user", "user@test.com", "hash");
        var before = DateTime.UtcNow;

        user.RecordLogin();

        user.LastLoginAt.Should().NotBeNull();
        user.LastLoginAt.Should().BeOnOrAfter(before);
        user.LastLoginAt.Should().BeOnOrBefore(DateTime.UtcNow);
    }

    // ── UpdateProfile ─────────────────────────────────────────────

    [Fact]
    public void UpdateProfile_WithBothValues_UpdatesBothFields()
    {
        var user = User.Create("user", "old@test.com", "hash", "Old Name");

        user.UpdateProfile("New Name", "new@test.com");

        user.FullName.Should().Be("New Name");
        user.Email.Should().Be("new@test.com");
    }

    [Fact]
    public void UpdateProfile_WithNullFullName_KeepsOriginal()
    {
        var user = User.Create("user", "email@test.com", "hash", "Original Name");

        user.UpdateProfile(null, "new@test.com");

        user.FullName.Should().Be("Original Name");
        user.Email.Should().Be("new@test.com");
    }

    [Fact]
    public void UpdateProfile_WithNullEmail_KeepsOriginal()
    {
        var user = User.Create("user", "original@test.com", "hash", "Name");

        user.UpdateProfile("New Name", null);

        user.Email.Should().Be("original@test.com");
        user.FullName.Should().Be("New Name");
    }

    [Fact]
    public void UpdateProfile_UpdatesUpdatedAt()
    {
        var user = User.Create("user", "email@test.com", "hash");
        var before = DateTime.UtcNow;

        user.UpdateProfile("New Name", null);

        user.UpdatedAt.Should().NotBeNull();
        user.UpdatedAt.Should().BeOnOrAfter(before);
    }

    // ── ChangePassword ────────────────────────────────────────────

    [Fact]
    public void ChangePassword_ValidHash_UpdatesPasswordHash()
    {
        var user = User.Create("user", "email@test.com", "old_hash");

        user.ChangePassword("new_hash");

        user.PasswordHash.Should().Be("new_hash");
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void ChangePassword_NullOrWhitespace_ThrowsArgumentException(string? newHash)
    {
        var user = User.Create("user", "email@test.com", "hash");
        var act = () => user.ChangePassword(newHash!);
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void ChangePassword_UpdatesUpdatedAt()
    {
        var user = User.Create("user", "email@test.com", "hash");
        var before = DateTime.UtcNow;

        user.ChangePassword("new_hash");

        user.UpdatedAt.Should().NotBeNull();
        user.UpdatedAt.Should().BeOnOrAfter(before);
    }

    // ── Deactivate ────────────────────────────────────────────────

    [Fact]
    public void Deactivate_SetsIsActiveToFalse()
    {
        var user = User.Create("user", "email@test.com", "hash");
        user.IsActive.Should().BeTrue();

        user.Deactivate();

        user.IsActive.Should().BeFalse();
    }

    [Fact]
    public void Deactivate_UpdatesUpdatedAt()
    {
        var user = User.Create("user", "email@test.com", "hash");
        var before = DateTime.UtcNow;

        user.Deactivate();

        user.UpdatedAt.Should().NotBeNull();
        user.UpdatedAt.Should().BeOnOrAfter(before);
    }

    // ── Default Values ────────────────────────────────────────────

    [Fact]
    public void Create_HasUniqueIds()
    {
        var user1 = User.Create("user1", "user1@test.com", "hash");
        var user2 = User.Create("user2", "user2@test.com", "hash");

        user1.Id.Should().NotBe(user2.Id);
    }

    [Fact]
    public void Create_SetsCreatedAt()
    {
        var before = DateTime.UtcNow;
        var user = User.Create("user", "email@test.com", "hash");
        user.CreatedAt.Should().BeOnOrAfter(before);
    }
}
