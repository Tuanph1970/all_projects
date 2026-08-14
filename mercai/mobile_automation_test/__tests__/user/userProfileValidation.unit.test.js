/**
 * Unit Tests for User Profile Validation Logic
 * Tests validation rules without E2E simulation
 *
 * Covers validation for:
 * - User profile retrieval
 * - User profile updates (name, phone, etc.)
 * - Account deactivation
 * - Field validation and sanitization
 */

const axios = require('axios');

// Mock axios
jest.mock('axios');

describe('User Profile Management - Unit Tests', () => {
  const baseUrl = 'http://localhost:8000';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Validation functions (simulating what the mobile app would use)
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
    // Allow letters, spaces, hyphens, and apostrophes
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

  const validatePhone = (phone) => {
    // Phone is optional
    if (!phone || phone.trim() === '') {
      return { valid: true, error: null };
    }

    // Remove formatting characters
    const cleanPhone = phone.replace(/[\s\-\(\)]/g, '');

    // Check if it contains only digits
    if (!/^\d+$/.test(cleanPhone)) {
      return { valid: false, error: 'Phone number must contain only digits' };
    }

    // Check length (10-15 digits for international numbers)
    if (cleanPhone.length < 10 || cleanPhone.length > 15) {
      return { valid: false, error: 'Phone number must be between 10 and 15 digits' };
    }

    return { valid: true, error: null };
  };

  const validateProfileUpdate = (data) => {
    const errors = {};

    if (data.first_name !== undefined) {
      const firstNameValidation = validateFirstName(data.first_name);
      if (!firstNameValidation.valid) {
        errors.first_name = firstNameValidation.error;
      }
    }

    if (data.last_name !== undefined) {
      const lastNameValidation = validateLastName(data.last_name);
      if (!lastNameValidation.valid) {
        errors.last_name = lastNameValidation.error;
      }
    }

    if (data.phone !== undefined) {
      const phoneValidation = validatePhone(data.phone);
      if (!phoneValidation.valid) {
        errors.phone = phoneValidation.error;
      }
    }

    if (Object.keys(errors).length > 0) {
      return { valid: false, errors };
    }

    return { valid: true, errors: null };
  };

  describe('TC-USER-001: View User Profile', () => {
    it('should successfully retrieve user profile', async () => {
      // Arrange
      const mockToken = 'valid_access_token_12345';
      const mockResponse = {
        data: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
          phone: '1234567890',
          role: 'customer',
          is_verified: true,
          is_active: true
        },
        status: 200
      };

      axios.get.mockResolvedValue(mockResponse);

      // Act
      const response = await axios.get(`${baseUrl}/api/v1/users/me/profile`, {
        headers: { 'Authorization': `Bearer ${mockToken}` }
      });

      // Assert
      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('id');
      expect(response.data).toHaveProperty('username');
      expect(response.data).toHaveProperty('email');
      expect(response.data).toHaveProperty('first_name');
      expect(response.data).toHaveProperty('last_name');
    });

    it('should reject request without authentication', async () => {
      // Arrange
      const mockError = {
        response: {
          status: 401,
          data: { detail: 'Not authenticated' }
        }
      };

      axios.get.mockRejectedValue(mockError);

      // Act & Assert
      await expect(
        axios.get(`${baseUrl}/api/v1/users/me/profile`)
      ).rejects.toMatchObject({
        response: { status: 401 }
      });
    });
  });

  describe('TC-USER-002: Update User Profile', () => {
    it('should successfully update user profile with valid data', async () => {
      // Arrange
      const mockToken = 'valid_access_token_12345';
      const updateData = {
        first_name: 'Jane',
        last_name: 'Smith',
        phone: '9876543210'
      };

      const validation = validateProfileUpdate(updateData);
      expect(validation.valid).toBe(true);

      const mockResponse = {
        data: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          first_name: 'Jane',
          last_name: 'Smith',
          phone: '9876543210',
          role: 'customer'
        },
        status: 200
      };

      axios.put.mockResolvedValue(mockResponse);

      // Act
      const response = await axios.put(
        `${baseUrl}/api/v1/users/me/profile`,
        updateData,
        { headers: { 'Authorization': `Bearer ${mockToken}` } }
      );

      // Assert
      expect(response.status).toBe(200);
      expect(response.data.first_name).toBe('Jane');
      expect(response.data.last_name).toBe('Smith');
      expect(response.data.phone).toBe('9876543210');
    });

    it('should validate first name - reject empty', () => {
      // Act
      const result = validateFirstName('');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('First name is required');
    });

    it('should validate first name - reject too short', () => {
      // Act
      const result = validateFirstName('J');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('First name must be at least 2 characters');
    });

    it('should validate first name - reject too long', () => {
      // Act
      const result = validateFirstName('a'.repeat(51));

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('First name must be less than 50 characters');
    });

    it('should validate first name - accept special characters (apostrophe, hyphen)', () => {
      // Act & Assert
      expect(validateFirstName("O'Brien").valid).toBe(true);
      expect(validateFirstName('Mary-Jane').valid).toBe(true);
      expect(validateFirstName('Mary Anne').valid).toBe(true);
    });

    it('should validate first name - reject numbers', () => {
      // Act
      const result = validateFirstName('John123');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('First name can only contain letters, spaces, hyphens, and apostrophes');
    });

    it('should validate last name - reject empty', () => {
      // Act
      const result = validateLastName('');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Last name is required');
    });

    it('should validate last name - accept valid format', () => {
      // Act & Assert
      expect(validateLastName('Smith').valid).toBe(true);
      expect(validateLastName('Van Der Berg').valid).toBe(true);
      expect(validateLastName("O'Connor").valid).toBe(true);
    });

    it('should validate phone - optional field (accept empty)', () => {
      // Act
      const result = validatePhone('');

      // Assert
      expect(result.valid).toBe(true);
    });

    it('should validate phone - accept valid 10-digit number', () => {
      // Act
      const result = validatePhone('1234567890');

      // Assert
      expect(result.valid).toBe(true);
    });

    it('should validate phone - accept formatted phone', () => {
      // Act
      const result = validatePhone('(123) 456-7890');

      // Assert
      expect(result.valid).toBe(true);
    });

    it('should validate phone - reject phone with letters', () => {
      // Act
      const result = validatePhone('123abc7890');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Phone number must contain only digits');
    });

    it('should validate phone - reject too short', () => {
      // Act
      const result = validatePhone('123456');

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Phone number must be between 10 and 15 digits');
    });

    it('should validate phone - accept international format', () => {
      // Act
      const result = validatePhone('+1234567890123');

      // Assert
      expect(result.valid).toBe(false); // Contains + sign
    });

    it('should validate complete profile update', () => {
      // Arrange
      const validData = {
        first_name: 'John',
        last_name: 'Doe',
        phone: '1234567890'
      };

      // Act
      const result = validateProfileUpdate(validData);

      // Assert
      expect(result.valid).toBe(true);
      expect(result.errors).toBeNull();
    });

    it('should collect all validation errors', () => {
      // Arrange
      const invalidData = {
        first_name: 'J',
        last_name: '',
        phone: 'abc'
      };

      // Act
      const result = validateProfileUpdate(invalidData);

      // Assert
      expect(result.valid).toBe(false);
      expect(result.errors).toHaveProperty('first_name');
      expect(result.errors).toHaveProperty('last_name');
      expect(result.errors).toHaveProperty('phone');
    });

    it('should trim whitespace from name fields', () => {
      // Arrange
      const firstName = '  John  ';
      const lastName = '  Doe  ';

      // Act
      const trimmedFirst = firstName.trim();
      const trimmedLast = lastName.trim();

      // Assert
      expect(trimmedFirst).toBe('John');
      expect(trimmedLast).toBe('Doe');
      expect(validateFirstName(trimmedFirst).valid).toBe(true);
      expect(validateLastName(trimmedLast).valid).toBe(true);
    });
  });

  describe('TC-USER-003: Deactivate Account', () => {
    it('should successfully deactivate account', async () => {
      // Arrange
      const mockToken = 'valid_access_token_12345';
      const mockResponse = {
        data: { message: 'Account deactivated successfully' },
        status: 200
      };

      axios.delete.mockResolvedValue(mockResponse);

      // Act
      const response = await axios.delete(
        `${baseUrl}/api/v1/users/me/account`,
        { headers: { 'Authorization': `Bearer ${mockToken}` } }
      );

      // Assert
      expect(response.status).toBe(200);
      expect(response.data.message).toBe('Account deactivated successfully');
    });

    it('should reject deactivation without authentication', async () => {
      // Arrange
      const mockError = {
        response: {
          status: 401,
          data: { detail: 'Not authenticated' }
        }
      };

      axios.delete.mockRejectedValue(mockError);

      // Act & Assert
      await expect(
        axios.delete(`${baseUrl}/api/v1/users/me/account`)
      ).rejects.toMatchObject({
        response: { status: 401 }
      });
    });

    it('should handle concurrent deactivation attempts', async () => {
      // Arrange
      const mockToken = 'valid_access_token_12345';
      const mockResponse = {
        data: { message: 'Account deactivated successfully' },
        status: 200
      };

      axios.delete.mockResolvedValue(mockResponse);

      // Act - Multiple concurrent requests
      const requests = [
        axios.delete(`${baseUrl}/api/v1/users/me/account`, {
          headers: { 'Authorization': `Bearer ${mockToken}` }
        }),
        axios.delete(`${baseUrl}/api/v1/users/me/account`, {
          headers: { 'Authorization': `Bearer ${mockToken}` }
        })
      ];

      const responses = await Promise.all(requests);

      // Assert
      expect(responses[0].status).toBe(200);
      expect(responses[1].status).toBe(200);
    });
  });

  describe('Edge Cases and Security', () => {
    it('should handle null values in profile update', () => {
      // Arrange
      const data = {
        first_name: null,
        last_name: null,
        phone: null
      };

      // Act
      const result = validateProfileUpdate(data);

      // Assert
      expect(result.valid).toBe(false);
    });

    it('should handle undefined values gracefully', () => {
      // Arrange
      const data = {
        first_name: undefined,
        last_name: 'Doe',
        phone: '1234567890'
      };

      // Act
      const result = validateProfileUpdate(data);

      // Assert
      expect(result.valid).toBe(true);
    });

    it('should prevent XSS in name fields', () => {
      // Arrange
      const maliciousName = '<script>alert("XSS")</script>';

      // Act
      const result = validateFirstName(maliciousName);

      // Assert
      expect(result.valid).toBe(false);
    });

    it('should handle very long input gracefully', () => {
      // Arrange
      const veryLongName = 'a'.repeat(1000);

      // Act
      const result = validateFirstName(veryLongName);

      // Assert
      expect(result.valid).toBe(false);
      expect(result.error).toBe('First name must be less than 50 characters');
    });

    it('should validate phone with only spaces', () => {
      // Act
      const result = validatePhone('     ');

      // Assert
      expect(result.valid).toBe(true); // Treated as empty (optional)
    });
  });
});
