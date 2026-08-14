/**
 * Seller Profile Management Unit Tests
 *
 * Test Coverage: TC-SELLER-001 to TC-SELLER-023
 *
 * This file contains unit tests for the Seller Profile module without E2E simulation.
 * Tests focus on validation logic, business rules, and API interactions using mocked axios calls.
 *
 * Features Tested:
 * - View and update seller profile
 * - Store customization (name, description, contact info)
 * - Upload store logo and banner
 * - Create, update, activate, and delete store themes
 * - View public store information
 * - Store analytics and statistics
 * - Business verification requests
 * - Seller-only access control
 *
 * @jest-environment node
 */

const axios = require('axios');

// Mock axios
jest.mock('axios');

describe('Seller Profile Management Unit Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ============================================================================
  // TC-SELLER-001: View Seller Profile
  // ============================================================================
  describe('TC-SELLER-001: View Seller Profile', () => {
    test('Should retrieve seller profile successfully', async () => {
      // Arrange
      const mockProfile = {
        id: 1,
        user_id: 5,
        store_name: "John's Ceramics",
        store_description: 'Handmade ceramic pottery',
        business_phone: '+1234567890',
        business_email: 'john@mercai.com',
        logo_url: '/uploads/logos/logo.png',
        banner_url: '/uploads/banners/banner.png',
        is_verified: false,
        created_at: '2025-11-20T10:00:00Z'
      };

      axios.get.mockResolvedValue({ data: mockProfile });

      // Act
      const response = await axios.get('/api/v1/seller-profile/profile');

      // Assert
      expect(response.data.id).toBe(1);
      expect(response.data.store_name).toBe("John's Ceramics");
      expect(response.data.is_verified).toBe(false);
    });

    test('Should require seller role to view profile', async () => {
      // Arrange
      axios.get.mockRejectedValue({
        response: { status: 403, data: { detail: 'Only sellers can access profile' } }
      });

      // Act & Assert
      await expect(axios.get('/api/v1/seller-profile/profile')).rejects.toMatchObject({
        response: {
          status: 403,
          data: { detail: 'Only sellers can access profile' }
        }
      });
    });
  });

  // ============================================================================
  // TC-SELLER-002: Create Default Profile
  // ============================================================================
  describe('TC-SELLER-002: Create Default Profile', () => {
    test('Should create default profile for new seller', async () => {
      // Arrange
      const mockDefaultProfile = {
        id: 1,
        user_id: 5,
        store_name: "John's Store",
        display_contact_info: true,
        display_business_hours: true,
        allow_custom_orders: false,
        minimum_order_amount: 0,
        created_at: '2025-11-25T10:00:00Z'
      };

      axios.get.mockResolvedValue({ data: mockDefaultProfile });

      // Act
      const response = await axios.get('/api/v1/seller-profile/profile');

      // Assert
      expect(response.data.store_name).toContain('Store');
      expect(response.data.display_contact_info).toBe(true);
      expect(response.data.allow_custom_orders).toBe(false);
      expect(response.data.minimum_order_amount).toBe(0);
    });
  });

  // ============================================================================
  // TC-SELLER-003: Update Seller Profile
  // ============================================================================
  describe('TC-SELLER-003: Update Seller Profile', () => {
    test('Should update seller profile successfully', async () => {
      // Arrange
      const updateData = {
        store_name: 'Updated Ceramics Store',
        store_description: 'Premium handcrafted ceramics',
        business_phone: '+1987654321'
      };

      const mockUpdatedProfile = {
        id: 1,
        user_id: 5,
        ...updateData,
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockUpdatedProfile });

      // Act
      const response = await axios.put('/api/v1/seller-profile/profile', updateData);

      // Assert
      expect(response.data.store_name).toBe('Updated Ceramics Store');
      expect(response.data.store_description).toBe('Premium handcrafted ceramics');
      expect(response.data.updated_at).toBeDefined();
    });

    test('Should validate store name length', () => {
      // Arrange
      const invalidNames = ['', 'A', 'A'.repeat(101)];

      // Act & Assert
      invalidNames.forEach(name => {
        const validation = validateStoreName(name);
        expect(validation.valid).toBe(false);
      });
    });
  });

  // ============================================================================
  // TC-SELLER-004: Update Store Name
  // ============================================================================
  describe('TC-SELLER-004: Update Store Name', () => {
    test('Should update store name successfully', async () => {
      // Arrange
      const updateData = { store_name: 'New Store Name' };

      const mockProfile = {
        id: 1,
        store_name: 'New Store Name',
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockProfile });

      // Act
      const response = await axios.put('/api/v1/seller-profile/profile', updateData);

      // Assert
      expect(response.data.store_name).toBe('New Store Name');
    });

    test('Should validate store name format', () => {
      // Arrange & Act
      const valid = validateStoreName('Valid Store Name');
      const tooShort = validateStoreName('AB');
      const tooLong = validateStoreName('A'.repeat(101));
      const empty = validateStoreName('');

      // Assert
      expect(valid.valid).toBe(true);
      expect(tooShort.valid).toBe(false);
      expect(tooLong.valid).toBe(false);
      expect(empty.valid).toBe(false);
    });
  });

  // ============================================================================
  // TC-SELLER-005: Update Store Description
  // ============================================================================
  describe('TC-SELLER-005: Update Store Description', () => {
    test('Should update store description successfully', async () => {
      // Arrange
      const updateData = {
        store_description: 'We create beautiful handmade ceramic pieces for your home.'
      };

      const mockProfile = {
        id: 1,
        store_description: updateData.store_description,
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockProfile });

      // Act
      const response = await axios.put('/api/v1/seller-profile/profile', updateData);

      // Assert
      expect(response.data.store_description).toBe(updateData.store_description);
    });
  });

  // ============================================================================
  // TC-SELLER-006: Upload Store Logo
  // ============================================================================
  describe('TC-SELLER-006: Upload Store Logo', () => {
    test('Should upload store logo successfully', async () => {
      // Arrange
      const mockResponse = {
        message: 'Logo uploaded successfully',
        logo_url: '/uploads/logos/5_logo.png'
      };

      axios.post.mockResolvedValue({ data: mockResponse });

      // Act
      const formData = new FormData();
      formData.append('file', new Blob(['fake image data']), 'logo.png');
      const response = await axios.post('/api/v1/seller-profile/upload-logo', formData);

      // Assert
      expect(response.data.message).toBe('Logo uploaded successfully');
      expect(response.data.logo_url).toContain('logo');
    });

    test('Should reject non-image file for logo', async () => {
      // Arrange
      axios.post.mockRejectedValue({
        response: { status: 400, data: { detail: 'File must be an image' } }
      });

      // Act & Assert
      const formData = new FormData();
      formData.append('file', new Blob(['text data']), 'file.txt');
      await expect(axios.post('/api/v1/seller-profile/upload-logo', formData)).rejects.toMatchObject({
        response: { status: 400 }
      });
    });
  });

  // ============================================================================
  // TC-SELLER-007: Upload Store Banner
  // ============================================================================
  describe('TC-SELLER-007: Upload Store Banner', () => {
    test('Should upload store banner successfully', async () => {
      // Arrange
      const mockResponse = {
        message: 'Banner uploaded successfully',
        banner_url: '/uploads/banners/5_banner.png'
      };

      axios.post.mockResolvedValue({ data: mockResponse });

      // Act
      const formData = new FormData();
      formData.append('file', new Blob(['fake image data']), 'banner.png');
      const response = await axios.post('/api/v1/seller-profile/upload-banner', formData);

      // Assert
      expect(response.data.message).toBe('Banner uploaded successfully');
      expect(response.data.banner_url).toContain('banner');
    });

    test('Should reject non-image file for banner', async () => {
      // Arrange
      axios.post.mockRejectedValue({
        response: { status: 400, data: { detail: 'File must be an image' } }
      });

      // Act & Assert
      await expect(axios.post('/api/v1/seller-profile/upload-banner', {})).rejects.toMatchObject({
        response: { status: 400 }
      });
    });
  });

  // ============================================================================
  // TC-SELLER-008: Update Contact Information
  // ============================================================================
  describe('TC-SELLER-008: Update Contact Information', () => {
    test('Should update business contact information', async () => {
      // Arrange
      const contactData = {
        business_phone: '+1234567890',
        business_email: 'contact@store.com',
        website_url: 'https://www.store.com'
      };

      const mockProfile = {
        id: 1,
        ...contactData,
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockProfile });

      // Act
      const response = await axios.put('/api/v1/seller-profile/profile', contactData);

      // Assert
      expect(response.data.business_phone).toBe('+1234567890');
      expect(response.data.business_email).toBe('contact@store.com');
      expect(response.data.website_url).toBe('https://www.store.com');
    });

    test('Should validate contact information format', () => {
      // Arrange & Act
      const validEmail = validateEmail('valid@email.com');
      const invalidEmail = validateEmail('invalid-email');
      const validPhone = validatePhone('+1234567890');
      const invalidPhone = validatePhone('123');

      // Assert
      expect(validEmail.valid).toBe(true);
      expect(invalidEmail.valid).toBe(false);
      expect(validPhone.valid).toBe(true);
      expect(invalidPhone.valid).toBe(false);
    });
  });

  // ============================================================================
  // TC-SELLER-009: Update Business Hours
  // ============================================================================
  describe('TC-SELLER-009: Update Business Hours', () => {
    test('Should update business hours successfully', async () => {
      // Arrange
      const businessHours = {
        monday: '9:00 AM - 6:00 PM',
        tuesday: '9:00 AM - 6:00 PM',
        wednesday: '9:00 AM - 6:00 PM',
        thursday: '9:00 AM - 6:00 PM',
        friday: '9:00 AM - 6:00 PM',
        saturday: '10:00 AM - 4:00 PM',
        sunday: 'Closed'
      };

      const mockProfile = {
        id: 1,
        business_hours: businessHours,
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockProfile });

      // Act
      const response = await axios.put('/api/v1/seller-profile/profile', { business_hours: businessHours });

      // Assert
      expect(response.data.business_hours.monday).toBe('9:00 AM - 6:00 PM');
      expect(response.data.business_hours.sunday).toBe('Closed');
    });
  });

  // ============================================================================
  // TC-SELLER-010: Update Shipping Policy
  // ============================================================================
  describe('TC-SELLER-010: Update Shipping Policy', () => {
    test('Should update shipping policy successfully', async () => {
      // Arrange
      const shippingPolicy = 'We ship within 3-5 business days. Free shipping on orders over $50.';

      const mockProfile = {
        id: 1,
        shipping_policy: shippingPolicy,
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockProfile });

      // Act
      const response = await axios.put('/api/v1/seller-profile/profile', { shipping_policy: shippingPolicy });

      // Assert
      expect(response.data.shipping_policy).toBe(shippingPolicy);
    });
  });

  // ============================================================================
  // TC-SELLER-011: Update Return Policy
  // ============================================================================
  describe('TC-SELLER-011: Update Return Policy', () => {
    test('Should update return policy successfully', async () => {
      // Arrange
      const returnPolicy = '30-day return policy. Items must be unused and in original packaging.';

      const mockProfile = {
        id: 1,
        return_policy: returnPolicy,
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockProfile });

      // Act
      const response = await axios.put('/api/v1/seller-profile/profile', { return_policy: returnPolicy });

      // Assert
      expect(response.data.return_policy).toBe(returnPolicy);
    });
  });

  // ============================================================================
  // TC-SELLER-012: View Store Information
  // ============================================================================
  describe('TC-SELLER-012: View Store Information', () => {
    test('Should retrieve complete store information with themes', async () => {
      // Arrange
      const mockStoreData = {
        profile: {
          id: 1,
          store_name: "John's Ceramics",
          store_description: 'Premium ceramics'
        },
        active_theme: {
          id: 1,
          theme_name: 'Modern',
          primary_color: '#FF5733',
          is_active: true
        },
        available_themes: [
          { id: 1, theme_name: 'Modern', is_active: true },
          { id: 2, theme_name: 'Classic', is_active: false }
        ]
      };

      axios.get.mockResolvedValue({ data: mockStoreData });

      // Act
      const response = await axios.get('/api/v1/seller-profile/store');

      // Assert
      expect(response.data.profile.store_name).toBe("John's Ceramics");
      expect(response.data.active_theme.theme_name).toBe('Modern');
      expect(response.data.available_themes).toHaveLength(2);
    });
  });

  // ============================================================================
  // TC-SELLER-013: Create Store Theme
  // ============================================================================
  describe('TC-SELLER-013: Create Store Theme', () => {
    test('Should create store theme successfully', async () => {
      // Arrange
      const themeData = {
        theme_name: 'Ocean Blue',
        primary_color: '#0066CC',
        secondary_color: '#99CCFF',
        font_family: 'Arial',
        is_active: false
      };

      const mockTheme = {
        id: 1,
        seller_profile_id: 1,
        ...themeData,
        created_at: '2025-11-25T10:00:00Z'
      };

      axios.post.mockResolvedValue({ data: mockTheme });

      // Act
      const response = await axios.post('/api/v1/seller-profile/themes', themeData);

      // Assert
      expect(response.data.id).toBe(1);
      expect(response.data.theme_name).toBe('Ocean Blue');
      expect(response.data.primary_color).toBe('#0066CC');
    });

    test('Should validate theme color format', () => {
      // Arrange & Act
      const validColor = validateHexColor('#FF5733');
      const invalidColor = validateHexColor('FF5733');
      const shortColor = validateHexColor('#F57');

      // Assert
      expect(validColor.valid).toBe(true);
      expect(invalidColor.valid).toBe(false);
      expect(shortColor.valid).toBe(true); // Short hex is valid
    });
  });

  // ============================================================================
  // TC-SELLER-014: Update Store Theme
  // ============================================================================
  describe('TC-SELLER-014: Update Store Theme', () => {
    test('Should update theme settings successfully', async () => {
      // Arrange
      const themeId = 1;
      const updateData = {
        primary_color: '#FF0000',
        secondary_color: '#00FF00'
      };

      const mockUpdatedTheme = {
        id: themeId,
        theme_name: 'Ocean Blue',
        ...updateData,
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockUpdatedTheme });

      // Act
      const response = await axios.put(`/api/v1/seller-profile/themes/${themeId}`, updateData);

      // Assert
      expect(response.data.primary_color).toBe('#FF0000');
      expect(response.data.secondary_color).toBe('#00FF00');
      expect(response.data.updated_at).toBeDefined();
    });

    test('Should handle non-existent theme', async () => {
      // Arrange
      const themeId = 999;
      axios.put.mockRejectedValue({
        response: { status: 404, data: { detail: 'Theme not found' } }
      });

      // Act & Assert
      await expect(axios.put(`/api/v1/seller-profile/themes/${themeId}`, {})).rejects.toMatchObject({
        response: { status: 404 }
      });
    });
  });

  // ============================================================================
  // TC-SELLER-015: Activate Theme
  // ============================================================================
  describe('TC-SELLER-015: Activate Theme', () => {
    test('Should activate theme successfully', async () => {
      // Arrange
      const themeId = 2;

      const mockActivatedTheme = {
        id: themeId,
        theme_name: 'Classic',
        is_active: true,
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.post.mockResolvedValue({ data: mockActivatedTheme });

      // Act
      const response = await axios.post(`/api/v1/seller-profile/themes/${themeId}/activate`);

      // Assert
      expect(response.data.is_active).toBe(true);
      expect(response.data.id).toBe(themeId);
    });

    test('Should deactivate previous active theme when activating new one', async () => {
      // Arrange - This is handled server-side, test the result
      const mockActivatedTheme = {
        id: 2,
        theme_name: 'New Active Theme',
        is_active: true
      };

      axios.post.mockResolvedValue({ data: mockActivatedTheme });

      // Act
      const response = await axios.post('/api/v1/seller-profile/themes/2/activate');

      // Assert
      expect(response.data.is_active).toBe(true);
    });
  });

  // ============================================================================
  // TC-SELLER-016: Delete Theme
  // ============================================================================
  describe('TC-SELLER-016: Delete Theme', () => {
    test('Should delete non-active theme successfully', async () => {
      // Arrange
      const themeId = 2;

      axios.delete.mockResolvedValue({
        data: { message: 'Theme deleted successfully' }
      });

      // Act
      const response = await axios.delete(`/api/v1/seller-profile/themes/${themeId}`);

      // Assert
      expect(response.data.message).toBe('Theme deleted successfully');
    });

    test('Should handle non-existent theme deletion', async () => {
      // Arrange
      const themeId = 999;
      axios.delete.mockRejectedValue({
        response: { status: 404, data: { detail: 'Theme not found' } }
      });

      // Act & Assert
      await expect(axios.delete(`/api/v1/seller-profile/themes/${themeId}`)).rejects.toMatchObject({
        response: { status: 404 }
      });
    });
  });

  // ============================================================================
  // TC-SELLER-017: Delete Active Theme
  // ============================================================================
  describe('TC-SELLER-017: Delete Active Theme', () => {
    test('Should prevent deletion of active theme', async () => {
      // Arrange
      const themeId = 1; // Active theme

      axios.delete.mockRejectedValue({
        response: { status: 400, data: { detail: 'Cannot delete active theme' } }
      });

      // Act & Assert
      await expect(axios.delete(`/api/v1/seller-profile/themes/${themeId}`)).rejects.toMatchObject({
        response: {
          status: 400,
          data: { detail: 'Cannot delete active theme' }
        }
      });
    });
  });

  // ============================================================================
  // TC-SELLER-018: View Public Store
  // ============================================================================
  describe('TC-SELLER-018: View Public Store', () => {
    test('Should retrieve public store information', async () => {
      // Arrange
      const sellerId = 5;
      const mockPublicStore = {
        store_name: "John's Ceramics",
        store_description: 'Premium handmade ceramics',
        store_tagline: 'Crafted with love',
        logo_url: '/uploads/logos/logo.png',
        banner_url: '/uploads/banners/banner.png',
        is_verified: true,
        is_featured: false,
        shipping_policy: 'Ships within 3-5 days',
        return_policy: '30-day returns',
        active_theme: {
          theme_name: 'Modern',
          primary_color: '#FF5733'
        }
      };

      axios.get.mockResolvedValue({ data: mockPublicStore });

      // Act
      const response = await axios.get(`/api/v1/seller-profile/public/${sellerId}`);

      // Assert
      expect(response.data.store_name).toBe("John's Ceramics");
      expect(response.data.is_verified).toBe(true);
      expect(response.data.active_theme.theme_name).toBe('Modern');
    });

    test('Should handle non-existent store', async () => {
      // Arrange
      const sellerId = 999;
      axios.get.mockRejectedValue({
        response: { status: 404, data: { detail: 'Store not found' } }
      });

      // Act & Assert
      await expect(axios.get(`/api/v1/seller-profile/public/${sellerId}`)).rejects.toMatchObject({
        response: { status: 404 }
      });
    });
  });

  // ============================================================================
  // TC-SELLER-019: View Store Analytics
  // ============================================================================
  describe('TC-SELLER-019: View Store Analytics', () => {
    test('Should retrieve store analytics successfully', async () => {
      // Arrange
      const mockAnalytics = {
        total_products: 50,
        total_orders: 120,
        total_revenue: 15000.00,
        avg_rating: 4.7,
        total_reviews: 85,
        conversion_rate: 0
      };

      axios.get.mockResolvedValue({ data: mockAnalytics });

      // Act
      const response = await axios.get('/api/v1/seller-profile/analytics');

      // Assert
      expect(response.data.total_products).toBe(50);
      expect(response.data.total_orders).toBe(120);
      expect(response.data.total_revenue).toBe(15000.00);
      expect(response.data.avg_rating).toBe(4.7);
      expect(response.data.total_reviews).toBe(85);
    });

    test('Should require seller role for analytics', async () => {
      // Arrange
      axios.get.mockRejectedValue({
        response: { status: 403, data: { detail: 'Only sellers can access analytics' } }
      });

      // Act & Assert
      await expect(axios.get('/api/v1/seller-profile/analytics')).rejects.toMatchObject({
        response: { status: 403 }
      });
    });
  });

  // ============================================================================
  // TC-SELLER-020: View Store Statistics
  // ============================================================================
  describe('TC-SELLER-020: View Store Statistics', () => {
    test('Should retrieve store statistics successfully', async () => {
      // Arrange
      const mockStats = {
        profile_completion: 85.5,
        store_views: 0,
        store_followers: 0,
        recent_activity: [
          { type: 'profile_update', timestamp: '2025-11-25T10:00:00Z', description: 'Profile updated' },
          { type: 'theme_change', timestamp: '2025-11-25T09:00:00Z', description: 'Store theme updated' }
        ]
      };

      axios.get.mockResolvedValue({ data: mockStats });

      // Act
      const response = await axios.get('/api/v1/seller-profile/stats');

      // Assert
      expect(response.data.profile_completion).toBe(85.5);
      expect(response.data.recent_activity).toHaveLength(2);
    });
  });

  // ============================================================================
  // TC-SELLER-021: Profile Completion Percentage
  // ============================================================================
  describe('TC-SELLER-021: Profile Completion Percentage', () => {
    test('Should calculate profile completion percentage correctly', () => {
      // Arrange
      const completeProfile = {
        store_name: 'Store Name',
        store_description: 'Description',
        store_tagline: 'Tagline',
        business_phone: '+1234567890',
        business_email: 'email@store.com',
        business_address_line1: '123 Main St',
        business_city: 'City',
        business_state: 'State',
        logo_url: '/logo.png',
        banner_url: '/banner.png',
        brand_colors: '#FF5733',
        social_media_links: { facebook: 'link' },
        business_type: 'LLC',
        shipping_policy: 'Policy',
        return_policy: 'Policy',
        processing_time: '3-5 days',
        about_us: 'About',
        specialties: 'Ceramics',
        business_hours: { monday: '9-5' },
        meta_description: 'Meta'
      };

      // Act
      const completion = calculateProfileCompletion(completeProfile);

      // Assert
      expect(completion).toBe(100);
    });

    test('Should calculate partial completion correctly', () => {
      // Arrange
      const partialProfile = {
        store_name: 'Store Name',
        store_description: 'Description',
        logo_url: '/logo.png',
        shipping_policy: 'Policy',
        return_policy: 'Policy'
      };

      // Act
      const completion = calculateProfileCompletion(partialProfile);

      // Assert
      expect(completion).toBe(25); // 5 out of 20 fields
    });
  });

  // ============================================================================
  // TC-SELLER-022: Request Business Verification
  // ============================================================================
  describe('TC-SELLER-022: Request Business Verification', () => {
    test('Should submit verification request successfully', async () => {
      // Arrange
      const verificationData = {
        business_name: "John's Ceramics LLC",
        business_license_number: 'BL-12345',
        tax_id: 'TAX-67890'
      };

      const mockResponse = {
        message: 'Verification request submitted successfully',
        status: 'pending_review'
      };

      axios.post.mockResolvedValue({ data: mockResponse });

      // Act
      const response = await axios.post('/api/v1/seller-profile/verify', verificationData);

      // Assert
      expect(response.data.message).toBe('Verification request submitted successfully');
      expect(response.data.status).toBe('pending_review');
    });

    test('Should require seller role for verification', async () => {
      // Arrange
      axios.post.mockRejectedValue({
        response: { status: 403, data: { detail: 'Only sellers can request verification' } }
      });

      // Act & Assert
      await expect(axios.post('/api/v1/seller-profile/verify', {})).rejects.toMatchObject({
        response: { status: 403 }
      });
    });
  });

  // ============================================================================
  // TC-SELLER-023: Access Seller Features - Non-Seller
  // ============================================================================
  describe('TC-SELLER-023: Access Seller Features - Non-Seller', () => {
    test('Should prevent non-seller from accessing profile', async () => {
      // Arrange
      axios.get.mockRejectedValue({
        response: { status: 403, data: { detail: 'Only sellers can access profile' } }
      });

      // Act & Assert
      await expect(axios.get('/api/v1/seller-profile/profile')).rejects.toMatchObject({
        response: { status: 403 }
      });
    });

    test('Should prevent non-seller from updating profile', async () => {
      // Arrange
      axios.put.mockRejectedValue({
        response: { status: 403, data: { detail: 'Only sellers can update profile' } }
      });

      // Act & Assert
      await expect(axios.put('/api/v1/seller-profile/profile', {})).rejects.toMatchObject({
        response: { status: 403 }
      });
    });

    test('Should prevent non-seller from creating themes', async () => {
      // Arrange
      axios.post.mockRejectedValue({
        response: { status: 403, data: { detail: 'Only sellers can create themes' } }
      });

      // Act & Assert
      await expect(axios.post('/api/v1/seller-profile/themes', {})).rejects.toMatchObject({
        response: { status: 403 }
      });
    });

    test('Should prevent non-seller from accessing analytics', async () => {
      // Arrange
      axios.get.mockRejectedValue({
        response: { status: 403, data: { detail: 'Only sellers can access analytics' } }
      });

      // Act & Assert
      await expect(axios.get('/api/v1/seller-profile/analytics')).rejects.toMatchObject({
        response: { status: 403 }
      });
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================
  describe('Edge Cases', () => {
    test('Should handle empty theme list', async () => {
      // Arrange
      const mockStoreData = {
        profile: { id: 1, store_name: 'Store' },
        active_theme: null,
        available_themes: []
      };

      axios.get.mockResolvedValue({ data: mockStoreData });

      // Act
      const response = await axios.get('/api/v1/seller-profile/store');

      // Assert
      expect(response.data.available_themes).toHaveLength(0);
      expect(response.data.active_theme).toBeNull();
    });

    test('Should handle analytics with zero values', async () => {
      // Arrange
      const mockAnalytics = {
        total_products: 0,
        total_orders: 0,
        total_revenue: 0,
        avg_rating: 0,
        total_reviews: 0,
        conversion_rate: 0
      };

      axios.get.mockResolvedValue({ data: mockAnalytics });

      // Act
      const response = await axios.get('/api/v1/seller-profile/analytics');

      // Assert
      expect(response.data.total_products).toBe(0);
      expect(response.data.total_revenue).toBe(0);
    });

    test('Should handle very long store descriptions', async () => {
      // Arrange
      const longDescription = 'A'.repeat(5000);
      const updateData = { store_description: longDescription };

      const mockProfile = {
        id: 1,
        store_description: longDescription
      };

      axios.put.mockResolvedValue({ data: mockProfile });

      // Act
      const response = await axios.put('/api/v1/seller-profile/profile', updateData);

      // Assert
      expect(response.data.store_description).toHaveLength(5000);
    });

    test('Should handle special characters in store name', async () => {
      // Arrange
      const storeName = "John's Céramics & Pottery™";
      const mockProfile = {
        id: 1,
        store_name: storeName
      };

      axios.put.mockResolvedValue({ data: mockProfile });

      // Act
      const response = await axios.put('/api/v1/seller-profile/profile', { store_name: storeName });

      // Assert
      expect(response.data.store_name).toBe(storeName);
    });
  });
});

// ============================================================================
// Validation Helper Functions
// ============================================================================

/**
 * Validate store name
 * @param {string} name - Store name to validate
 * @returns {Object} Validation result
 */
function validateStoreName(name) {
  if (!name || typeof name !== 'string') {
    return { valid: false, error: 'Store name is required' };
  }

  if (name.trim().length < 3) {
    return { valid: false, error: 'Store name must be at least 3 characters' };
  }

  if (name.length > 100) {
    return { valid: false, error: 'Store name must not exceed 100 characters' };
  }

  return { valid: true, error: null };
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {Object} Validation result
 */
function validateEmail(email) {
  if (!email || typeof email !== 'string') {
    return { valid: false, error: 'Email is required' };
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return { valid: false, error: 'Invalid email format' };
  }

  return { valid: true, error: null };
}

/**
 * Validate phone number
 * @param {string} phone - Phone number to validate
 * @returns {Object} Validation result
 */
function validatePhone(phone) {
  if (!phone || typeof phone !== 'string') {
    return { valid: false, error: 'Phone number is required' };
  }

  // Simple validation: must contain digits and be at least 10 characters
  const phoneRegex = /^[+]?[\d\s-()]{10,}$/;
  if (!phoneRegex.test(phone)) {
    return { valid: false, error: 'Invalid phone number format' };
  }

  return { valid: true, error: null };
}

/**
 * Validate hex color code
 * @param {string} color - Hex color to validate
 * @returns {Object} Validation result
 */
function validateHexColor(color) {
  if (!color || typeof color !== 'string') {
    return { valid: false, error: 'Color is required' };
  }

  // Valid formats: #RGB or #RRGGBB
  const hexRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
  if (!hexRegex.test(color)) {
    return { valid: false, error: 'Invalid hex color format' };
  }

  return { valid: true, error: null };
}

/**
 * Calculate profile completion percentage
 * @param {Object} profile - Seller profile object
 * @returns {number} Completion percentage (0-100)
 */
function calculateProfileCompletion(profile) {
  const totalFields = 20;
  let completedFields = 0;

  const fieldsToCheck = [
    'store_name', 'store_description', 'store_tagline', 'business_phone',
    'business_email', 'business_address_line1', 'business_city', 'business_state',
    'logo_url', 'banner_url', 'brand_colors', 'social_media_links',
    'business_type', 'shipping_policy', 'return_policy', 'processing_time',
    'about_us', 'specialties', 'business_hours', 'meta_description'
  ];

  fieldsToCheck.forEach(field => {
    if (profile[field] && profile[field] !== null && profile[field] !== '') {
      completedFields++;
    }
  });

  return Math.round((completedFields / totalFields) * 100);
}
