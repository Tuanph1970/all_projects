import apiClient, { handleApiResponse, handleApiError } from './apiClient';

class UserService {
  // Get user profile
  async getUserProfile() {
    try {
      const response = await apiClient.get('/users/profile');
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Update user profile
  async updateUserProfile(profileData) {
    try {
      const response = await apiClient.put('/users/profile', profileData);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Upload profile picture
  async uploadProfilePicture(imageUri) {
    try {
      const formData = new FormData();
      
      const filename = imageUri.split('/').pop();
      const match = /\\.([\\w\\d_-]+)$/i.exec(filename);
      const type = match ? `image/${match[1]}` : 'image/jpeg';
      
      formData.append('profilePicture', {
        uri: imageUri,
        name: filename,
        type,
      });
      
      const response = await apiClient.post('/users/profile/picture', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Change password
  async changePassword(currentPassword, newPassword) {
    try {
      const response = await apiClient.post('/users/change-password', {
        currentPassword,
        newPassword,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get user statistics
  async getUserStats() {
    try {
      const response = await apiClient.get('/users/stats');
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Update user preferences
  async updateUserPreferences(preferences) {
    try {
      const response = await apiClient.put('/users/preferences', preferences);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get user preferences
  async getUserPreferences() {
    try {
      const response = await apiClient.get('/users/preferences');
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get user achievements
  async getUserAchievements() {
    try {
      const response = await apiClient.get('/users/achievements');
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get user activity history
  async getUserActivity({ page = 1, limit = 20, type } = {}) {
    try {
      const params = {
        page,
        limit,
      };
      
      if (type) {
        params.type = type;
      }
      
      const response = await apiClient.get('/users/activity', { params });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Delete user account
  async deleteAccount(password) {
    try {
      const response = await apiClient.delete('/users/account', {
        data: { password },
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Export user data
  async exportUserData() {
    try {
      const response = await apiClient.get('/users/export', {
        responseType: 'blob',
      });
      
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // Update notification settings
  async updateNotificationSettings(settings) {
    try {
      const response = await apiClient.put('/users/notifications', settings);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get notification settings
  async getNotificationSettings() {
    try {
      const response = await apiClient.get('/users/notifications');
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Register push notification token
  async registerPushToken(token, deviceInfo) {
    try {
      const response = await apiClient.post('/users/push-token', {
        token,
        ...deviceInfo,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Unregister push notification token
  async unregisterPushToken(token) {
    try {
      const response = await apiClient.delete('/users/push-token', {
        data: { token },
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get user leaderboard position
  async getLeaderboardPosition() {
    try {
      const response = await apiClient.get('/users/leaderboard/position');
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get global leaderboard
  async getLeaderboard({ page = 1, limit = 50, period = 'all' } = {}) {
    try {
      const response = await apiClient.get('/users/leaderboard', {
        params: { page, limit, period },
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }
}

export const userService = new UserService();