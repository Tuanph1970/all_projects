import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

// Profile interfaces
class SellerProfileService {
  // Get seller profile
  async getProfile() {
    return await apiClient.get(API_CONFIG.ENDPOINTS.SELLER_PROFILE);
  }

  // Update seller profile
  async updateProfile(profileUpdate) {
    return await apiClient.put(API_CONFIG.ENDPOINTS.SELLER_PROFILE, profileUpdate);
  }

  // Get complete store information
  async getStore() {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_PROFILE}/store`);
  }

  // Save theme to profile's brand_colors field
  async saveTheme(themeData) {
    // Get current profile to preserve other data
    const currentProfile = await this.getProfile();
    const profile = currentProfile.data || currentProfile;

    // Store theme data in brand_colors field as JSON
    const brandColors = {
      primary_color: themeData.primary_color,
      secondary_color: themeData.secondary_color,
      accent_color: themeData.accent_color,
      background_color: themeData.background_color,
      text_color: themeData.text_color,
      theme_name: themeData.theme_name,
      layout_style: themeData.layout_style,
      header_style: themeData.header_style,
      footer_style: themeData.footer_style,
      heading_font: themeData.heading_font,
      body_font: themeData.body_font,
    };

    return await this.updateProfile({ brand_colors: brandColors });
  }

  // Get theme from profile's brand_colors field
  async getTheme() {
    const response = await this.getProfile();
    const profile = response.data || response;
    return profile.brand_colors || null;
  }

  // Legacy methods for backward compatibility (using profile update)
  async createTheme(themeCreate) {
    return await this.saveTheme(themeCreate);
  }

  async updateTheme(themeId, themeUpdate) {
    return await this.saveTheme(themeUpdate);
  }

  async activateTheme(themeId) {
    // With single theme approach, theme is always active
    return { success: true };
  }

  async deleteTheme(themeId) {
    // Clear brand_colors to delete theme
    return await this.updateProfile({ brand_colors: null });
  }

  // Get store (for customers)
  async getPublicStore(sellerId) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_PROFILE}/public/${sellerId}`);
  }

  // Get store analytics
  async getStoreAnalytics() {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_PROFILE}/analytics`);
  }

  // Get store stats
  async getStoreStats() {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_PROFILE}/stats`);
  }

  // Upload store logo
  async uploadLogo(file) {
    const formData = new FormData();
    formData.append('file', file);
    // Note: upload-logo is under /api/v1/seller, not /api/v1/seller/profile
    return await apiClient.upload(`${API_CONFIG.ENDPOINTS.SELLER}/upload-logo`, formData);
  }

  // Upload store banner
  async uploadBanner(file) {
    const formData = new FormData();
    formData.append('file', file);
    // Note: upload-banner is under /api/v1/seller, not /api/v1/seller/profile
    return await apiClient.upload(`${API_CONFIG.ENDPOINTS.SELLER}/upload-banner`, formData);
  }

  // Request business verification
  async requestVerification(verificationRequest) {
    return await apiClient.post(`${API_CONFIG.ENDPOINTS.SELLER_PROFILE}/verify`, verificationRequest);
  }

  // Helper methods for profile management
  calculateProfileCompletion(profile) {
    const fields = [
      'store_name',
      'store_description',
      'store_tagline',
      'business_phone',
      'business_email',
      'business_address_line1',
      'business_city',
      'business_state',
      'logo_url',
      'banner_url',
      'brand_colors',
      'social_media_links',
      'business_type',
      'shipping_policy',
      'return_policy',
      'processing_time',
      'about_us',
      'specialties',
      'business_hours',
      'meta_description'
    ];

    const completedFields = fields.filter(field => {
      const value = profile[field];
      if (Array.isArray(value)) return value.length > 0;
      if (typeof value === 'object' && value !== null) return Object.keys(value).length > 0;
      return value && value.toString().trim().length > 0;
    });

    return Math.round((completedFields.length / fields.length) * 100);
  }

  getBusinessHoursForDay(businessHours, day) {
    const defaultHours = { closed: true, open: null, close: null };
    if (!businessHours) return defaultHours;
    return businessHours[day.toLowerCase()] || defaultHours;
  }

  formatBusinessHours(hours) {
    if (hours.closed) return 'Closed';
    if (!hours.open || !hours.close) return 'Hours not set';
    return `${hours.open} - ${hours.close}`;
  }

  isStoreOpen(businessHours) {
    if (!businessHours) return false;
    
    const now = new Date();
    const dayName = now.toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
    const currentTime = now.toTimeString().substring(0, 5); // HH:MM format
    
    const todayHours = this.getBusinessHoursForDay(businessHours, dayName);
    
    if (todayHours.closed || !todayHours.open || !todayHours.close) {
      return false;
    }
    
    return currentTime >= todayHours.open && currentTime <= todayHours.close;
  }

  getStoreStatus(businessHours) {
    const isOpen = this.isStoreOpen(businessHours);
    
    if (isOpen) {
      return { 
        isOpen: true, 
        status: 'Open',
        nextChange: 'Closes at closing time'
      };
    } else {
      return { 
        isOpen: false, 
        status: 'Closed',
        nextChange: 'Opens at opening time'
      };
    }
  }

  createThemePreview(theme) {
    return {
      theme_name: theme.theme_name || 'Custom Theme',
      is_active: theme.is_active || false,
      primary_color: theme.primary_color || '#000000',
      secondary_color: theme.secondary_color || '#666666',
      accent_color: theme.accent_color || '#0066CC',
      background_color: theme.background_color || '#FFFFFF',
      text_color: theme.text_color || '#333333',
      font_family: theme.font_family || 'Arial, sans-serif',
      heading_font: theme.heading_font || 'Arial, sans-serif',
      body_font: theme.body_font || 'Arial, sans-serif',
      layout_style: theme.layout_style || 'modern',
      header_style: theme.header_style || 'default',
      footer_style: theme.footer_style || 'default'
    };
  }

  generateThemeCSS(theme) {
    // Generate CSS preview for theme
    return `
      :root {
        --primary-color: ${theme.primary_color};
        --secondary-color: ${theme.secondary_color};
        --accent-color: ${theme.accent_color};
        --background-color: ${theme.background_color};
        --text-color: ${theme.text_color};
        --font-family: ${theme.font_family};
        --heading-font: ${theme.heading_font};
        --body-font: ${theme.body_font};
      }
    `;
  }

  validateProfile(profile) {
    const errors = [];

    if (profile.business_email && !this.isValidEmail(profile.business_email)) {
      errors.push('Invalid business email format');
    }

    if (profile.website_url && !this.isValidUrl(profile.website_url)) {
      errors.push('Invalid website URL format');
    }

    if (profile.business_phone && !this.isValidPhone(profile.business_phone)) {
      errors.push('Invalid phone number format');
    }

    if (profile.minimum_order_amount && profile.minimum_order_amount < 0) {
      errors.push('Minimum order amount must be positive');
    }

    return errors;
  }

  isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  isValidUrl(url) {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  isValidPhone(phone) {
    const phoneRegex = /^[\d\s\-\+\(\)]+$/;
    return phoneRegex.test(phone) && phone.length >= 10;
  }

  // Color helpers for branding
  generateColorPalette(primaryColor) {
    // Simple color palette generation based on primary color
    // In a real app, you might use a color theory library
    return {
      primary: primaryColor,
      secondary: this.adjustBrightness(primaryColor, -20),
      accent: this.adjustBrightness(primaryColor, 30),
      background: '#FFFFFF',
      text: '#333333'
    };
  }

  adjustBrightness(hex, percent) {
    // Simple brightness adjustment
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
      (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
      (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
  }

  adjustHue(hex, degrees) {
    // Simple hue adjustment (this is a simplified version)
    // In a real app, you'd use proper HSL conversion
    return hex; // Placeholder
  }
}

export default new SellerProfileService();