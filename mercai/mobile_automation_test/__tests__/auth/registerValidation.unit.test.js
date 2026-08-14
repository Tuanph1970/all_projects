/**
 * Unit Tests for Register Validation Logic
 * Tests: TC-AUTH-015 to TC-AUTH-027
 *
 * Covers validation for:
 * - Name validation (with special characters)
 * - Username validation
 * - Email validation
 * - Password strength
 * - Password confirmation matching
 * - Role selection
 */

describe('Register Validation - Unit Tests', () => {
  // Validation functions
  const validateFirstName = (firstName) => {
    if (!firstName || firstName.trim() === '') {
      return { valid: false, error: 'First name is required' };
    }
    if (firstName.length < 2) {
      return { valid: false, error: 'First name must be at least 2 characters' };
    }
    if (firstName.length > 50) {
      return { valid: false, error: 'First name must be less than 50 characters' };
    }
    // Allow letters, spaces, hyphens, and apostrophes (for names like O'Brien, Smith-Jones)
    const nameRegex = /^[a-zA-Z\s'-]+$/;
    if (!nameRegex.test(firstName)) {
      return { valid: false, error: 'First name can only contain letters, spaces, hyphens, and apostrophes' };
    }
    return { valid: true, error: null };
  };

  const validateLastName = (lastName) => {
    if (!lastName || lastName.trim() === '') {
      return { valid: false, error: 'Last name is required' };
    }
    if (lastName.length < 2) {
      return { valid: false, error: 'Last name must be at least 2 characters' };
    }
    if (lastName.length > 50) {
      return { valid: false, error: 'Last name must be less than 50 characters' };
    }
    const nameRegex = /^[a-zA-Z\s'-]+$/;
    if (!nameRegex.test(lastName)) {
      return { valid: false, error: 'Last name can only contain letters, spaces, hyphens, and apostrophes' };
    }
    return { valid: true, error: null };
  };

  const validateUsername = (username) => {
    if (!username || username.trim() === '') {
      return { valid: false, error: 'Username is required' };
    }
    if (username.length < 3) {
      return { valid: false, error: 'Username must be at least 3 characters' };
    }
    if (username.length > 30) {
      return { valid: false, error: 'Username must be less than 30 characters' };
    }
    // Username can contain letters, numbers, underscores, and hyphens
    const usernameRegex = /^[a-zA-Z0-9_-]+$/;
    if (!usernameRegex.test(username)) {
      return { valid: false, error: 'Username can only contain letters, numbers, underscores, and hyphens' };
    }
    // Username must start with a letter
    if (!/^[a-zA-Z]/.test(username)) {
      return { valid: false, error: 'Username must start with a letter' };
    }
    return { valid: true, error: null };
  };

  const validateEmail = (email) => {
    if (!email || email.trim() === '') {
      return { valid: false, error: 'Email is required' };
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return { valid: false, error: 'Invalid email address' };
    }
    return { valid: true, error: null };
  };

  const validatePassword = (password) => {
    if (!password || password.trim() === '') {
      return { valid: false, error: 'Password is required' };
    }
    if (password.length < 8) {
      return { valid: false, error: 'Password must be at least 8 characters' };
    }
    // Check for password strength
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);

    if (!hasUpperCase || !hasLowerCase || !hasNumber) {
      return {
        valid: false,
        error: 'Password must contain at least one uppercase letter, one lowercase letter, and one number'
      };
    }

    return { valid: true, error: null };
  };

  const validatePasswordConfirmation = (password, confirmPassword) => {
    if (!confirmPassword || confirmPassword.trim() === '') {
      return { valid: false, error: 'Password confirmation is required' };
    }
    if (password !== confirmPassword) {
      return { valid: false, error: 'Passwords do not match' };
    }
    return { valid: true, error: null };
  };

  const validatePhoneNumber = (phone) => {
    if (!phone) {
      return { valid: true, error: null }; // Phone is optional
    }
    const phoneRegex = /^[0-9]{10,15}$/;
    if (!phoneRegex.test(phone.replace(/[\s-()]/g, ''))) {
      return { valid: false, error: 'Invalid phone number format' };
    }
    return { valid: true, error: null };
  };

  const validateRole = (role) => {
    const validRoles = ['customer', 'seller', 'dual'];
    if (!role) {
      return { valid: false, error: 'Role is required' };
    }
    if (!validRoles.includes(role)) {
      return { valid: false, error: 'Invalid role selected' };
    }
    return { valid: true, error: null };
  };

  describe('TC-AUTH-015: Name Validation with Special Characters', () => {
    it('should accept name with apostrophe (O\'Brien)', () => {
      // Act
      const result = validateFirstName('O\'Brien');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept name with hyphen (Smith-Jones)', () => {
      // Act
      const result = validateLastName('Smith-Jones');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept name with multiple parts (Mary Anne)', () => {
      // Act
      const result = validateFirstName('Mary Anne');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept name with multiple hyphens (Jean-Claude-Marie)', () => {
      // Act
      const result = validateFirstName('Jean-Claude-Marie');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should reject name with numbers', () => {
      // Act
      const result = validateFirstName('John123');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toContain('letters, spaces, hyphens, and apostrophes');
    });

    it('should reject name with special characters', () => {
      // Act
      const result = validateFirstName('John@Smith');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toContain('letters, spaces, hyphens, and apostrophes');
    });
  });

  describe('TC-AUTH-016: Empty Field Validations', () => {
    it('should reject empty first name', () => {
      // Act
      const result = validateFirstName('');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('First name is required');
    });

    it('should reject empty last name', () => {
      // Act
      const result = validateLastName('');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Last name is required');
    });

    it('should reject empty username', () => {
      // Act
      const result = validateUsername('');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Username is required');
    });

    it('should reject empty email', () => {
      // Act
      const result = validateEmail('');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Email is required');
    });

    it('should reject empty password', () => {
      // Act
      const result = validatePassword('');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Password is required');
    });

    it('should reject empty password confirmation', () => {
      // Act
      const result = validatePasswordConfirmation('password123', '');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Password confirmation is required');
    });
  });

  describe('TC-AUTH-017: Field Format Validations', () => {
    it('should reject first name shorter than 2 characters', () => {
      // Act
      const result = validateFirstName('J');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('First name must be at least 2 characters');
    });

    it('should reject first name longer than 50 characters', () => {
      // Act
      const result = validateFirstName('a'.repeat(51));

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('First name must be less than 50 characters');
    });

    it('should reject username shorter than 3 characters', () => {
      // Act
      const result = validateUsername('ab');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Username must be at least 3 characters');
    });

    it('should reject username longer than 30 characters', () => {
      // Act
      const result = validateUsername('a'.repeat(31));

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Username must be less than 30 characters');
    });

    it('should reject username not starting with letter', () => {
      // Act
      const result = validateUsername('123user');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Username must start with a letter');
    });

    it('should reject username with spaces', () => {
      // Act
      const result = validateUsername('user name');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toContain('letters, numbers, underscores, and hyphens');
    });

    it('should reject username with special characters', () => {
      // Act
      const result = validateUsername('user@name');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toContain('letters, numbers, underscores, and hyphens');
    });

    it('should accept valid username with underscores', () => {
      // Act
      const result = validateUsername('test_user_123');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept valid username with hyphens', () => {
      // Act
      const result = validateUsername('test-user-123');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });
  });

  describe('Email Format Validation', () => {
    it('should accept valid email', () => {
      // Act
      const result = validateEmail('user@example.com');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should reject email without @', () => {
      // Act
      const result = validateEmail('userexample.com');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Invalid email address');
    });

    it('should reject email without domain', () => {
      // Act
      const result = validateEmail('user@');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Invalid email address');
    });

    it('should reject email without TLD', () => {
      // Act
      const result = validateEmail('user@example');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Invalid email address');
    });

    it('should accept email with subdomain', () => {
      // Act
      const result = validateEmail('user@mail.example.com');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept email with plus sign', () => {
      // Act
      const result = validateEmail('user+tag@example.com');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });
  });

  describe('Password Strength Validation', () => {
    it('should reject password shorter than 8 characters', () => {
      // Act
      const result = validatePassword('Pass1');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Password must be at least 8 characters');
    });

    it('should reject password without uppercase letter', () => {
      // Act
      const result = validatePassword('password123');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toContain('uppercase letter');
    });

    it('should reject password without lowercase letter', () => {
      // Act
      const result = validatePassword('PASSWORD123');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toContain('lowercase letter');
    });

    it('should reject password without number', () => {
      // Act
      const result = validatePassword('Password');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toContain('number');
    });

    it('should accept strong password', () => {
      // Act
      const result = validatePassword('Password123');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept password with special characters', () => {
      // Act
      const result = validatePassword('Password123!@#');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });
  });

  describe('TC-AUTH-018: Password Confirmation Validation', () => {
    it('should accept matching passwords', () => {
      // Act
      const result = validatePasswordConfirmation('Password123', 'Password123');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should reject mismatched passwords', () => {
      // Act
      const result = validatePasswordConfirmation('Password123', 'Password456');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Passwords do not match');
    });

    it('should reject case-sensitive mismatch', () => {
      // Act
      const result = validatePasswordConfirmation('Password123', 'password123');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Passwords do not match');
    });

    it('should reject password with trailing space mismatch', () => {
      // Act
      const result = validatePasswordConfirmation('Password123', 'Password123 ');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Passwords do not match');
    });
  });

  describe('Phone Number Validation (Optional)', () => {
    it('should accept valid 10-digit phone number', () => {
      // Act
      const result = validatePhoneNumber('1234567890');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept phone number with formatting', () => {
      // Act
      const result = validatePhoneNumber('(123) 456-7890');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept international phone number', () => {
      // Act
      const result = validatePhoneNumber('123456789012345');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept empty phone (optional field)', () => {
      // Act
      const result = validatePhoneNumber('');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should reject phone with letters', () => {
      // Act
      const result = validatePhoneNumber('123abc7890');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Invalid phone number format');
    });

    it('should reject phone shorter than 10 digits', () => {
      // Act
      const result = validatePhoneNumber('123456789');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Invalid phone number format');
    });
  });

  describe('Role Validation', () => {
    it('should accept customer role', () => {
      // Act
      const result = validateRole('customer');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept seller role', () => {
      // Act
      const result = validateRole('seller');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should accept dual role', () => {
      // Act
      const result = validateRole('dual');

      // Assert
      expect(result.valid).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should reject invalid role', () => {
      // Act
      const result = validateRole('admin');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Invalid role selected');
    });

    it('should reject empty role', () => {
      // Act
      const result = validateRole('');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Role is required');
    });
  });

  describe('TC-AUTH-025: Edge Case - Whitespace Trimming', () => {
    it('should handle username with leading/trailing whitespace', () => {
      // Arrange
      const username = '  test_user  ';

      // Act
      const trimmed = username.trim();
      const result = validateUsername(trimmed);

      // Assert
      expect(trimmed).toBe('test_user');
      expect(result.valid).toBe(true);
    });

    it('should handle email with leading/trailing whitespace', () => {
      // Arrange
      const email = '  user@example.com  ';

      // Act
      const trimmed = email.trim();
      const result = validateEmail(trimmed);

      // Assert
      expect(trimmed).toBe('user@example.com');
      expect(result.valid).toBe(true);
    });

    it('should handle name with leading/trailing whitespace', () => {
      // Arrange
      const name = '  John  ';

      // Act
      const trimmed = name.trim();
      const result = validateFirstName(trimmed);

      // Assert
      expect(trimmed).toBe('John');
      expect(result.valid).toBe(true);
    });
  });

  describe('Complete Registration Validation', () => {
    it('should validate complete valid registration data', () => {
      // Arrange
      const registrationData = {
        firstName: 'John',
        lastName: 'Doe',
        username: 'johndoe',
        email: 'john@example.com',
        password: 'Password123',
        confirmPassword: 'Password123',
        phone: '1234567890',
        role: 'customer'
      };

      // Act
      const validations = {
        firstName: validateFirstName(registrationData.firstName),
        lastName: validateLastName(registrationData.lastName),
        username: validateUsername(registrationData.username),
        email: validateEmail(registrationData.email),
        password: validatePassword(registrationData.password),
        confirmPassword: validatePasswordConfirmation(registrationData.password, registrationData.confirmPassword),
        phone: validatePhoneNumber(registrationData.phone),
        role: validateRole(registrationData.role)
      };

      // Assert
      Object.values(validations).forEach(validation => {
        expect(validation.valid).toBe(true);
        expect(validation.error).toBeNull();
      });
    });

    it('should collect all validation errors', () => {
      // Arrange
      const registrationData = {
        firstName: '',
        lastName: 'D',
        username: '12',
        email: 'invalid-email',
        password: 'weak',
        confirmPassword: 'different',
        phone: 'invalid',
        role: 'invalid'
      };

      // Act
      const validations = {
        firstName: validateFirstName(registrationData.firstName),
        lastName: validateLastName(registrationData.lastName),
        username: validateUsername(registrationData.username),
        email: validateEmail(registrationData.email),
        password: validatePassword(registrationData.password),
        confirmPassword: validatePasswordConfirmation(registrationData.password, registrationData.confirmPassword),
        phone: validatePhoneNumber(registrationData.phone),
        role: validateRole(registrationData.role)
      };

      // Assert
      expect(validations.firstName.valid).toBe(false);
      expect(validations.lastName.valid).toBe(false);
      expect(validations.username.valid).toBe(false);
      expect(validations.email.valid).toBe(false);
      expect(validations.password.valid).toBe(false);
      expect(validations.confirmPassword.valid).toBe(false);
      expect(validations.phone.valid).toBe(false);
      expect(validations.role.valid).toBe(false);
    });
  });
});
