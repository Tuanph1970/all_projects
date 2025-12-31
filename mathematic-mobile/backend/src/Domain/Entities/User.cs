using Domain.Common;
using Domain.Common.Interfaces;

namespace Domain.Entities;

public class User : BaseEntity
{
    public string Username { get; private set; } = string.Empty;
    public string Email { get; private set; } = string.Empty;
    public string PasswordHash { get; private set; } = string.Empty;
    public bool IsActive { get; private set; }
    public DateTime? LastLoginAt { get; private set; }
    
    // Navigation properties
    public virtual ICollection<Problem> Problems { get; private set; } = new List<Problem>();
    
    private User()
    {
        // Private constructor for EF Core
    }
    
    public User(string username, string email, string passwordHash)
    {
        Username = username ?? throw new ArgumentNullException(nameof(username));
        Email = email ?? throw new ArgumentNullException(nameof(email));
        PasswordHash = passwordHash ?? throw new ArgumentNullException(nameof(passwordHash));
        IsActive = true;
        CreatedAt = DateTime.UtcNow;
    }
    
    public void UpdatePassword(string newPasswordHash)
    {
        PasswordHash = newPasswordHash ?? throw new ArgumentNullException(nameof(newPasswordHash));
        UpdatedAt = DateTime.UtcNow;
    }
    
    public void UpdateLastLogin()
    {
        LastLoginAt = DateTime.UtcNow;
        UpdatedAt = DateTime.UtcNow;
    }
    
    public void DeactivateUser()
    {
        IsActive = false;
        UpdatedAt = DateTime.UtcNow;
    }
    
    public void ActivateUser()
    {
        IsActive = true;
        UpdatedAt = DateTime.UtcNow;
    }
    
    public void UpdateEmail(string newEmail)
    {
        Email = newEmail ?? throw new ArgumentNullException(nameof(newEmail));
        UpdatedAt = DateTime.UtcNow;
    }
}