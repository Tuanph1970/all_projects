import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { UserRole } from '../../types/auth.js';
import { authService } from '../../services/authService.js';
import { secureStorage } from '../../utils/secureStorage.js';

const initialState = {
  user: null,
  tokens: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

// Async thunks
export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials, { rejectWithValue }) => {
    try {
      const response = await authService.login(credentials);
      
      // Store tokens securely
      await secureStorage.setTokens(response.tokens);
      
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Login failed');
    }
  }
);

export const registerUser = createAsyncThunk(
  'auth/registerUser',
  async (userData, { rejectWithValue }) => {
    try {
      // Clear any existing tokens before registration
      await secureStorage.clearTokens();

      const response = await authService.register(userData);
      return response;
    } catch (error) {
      console.error('🔴 [authSlice] registerUser error:', error);

      // Extract the most specific error message available
      let errorMessage = 'Registration failed';

      if (error.response?.data) {
        // Try different error response formats
        if (error.response.data.detail) {
          errorMessage = typeof error.response.data.detail === 'string'
            ? error.response.data.detail
            : JSON.stringify(error.response.data.detail);
        } else if (error.response.data.message) {
          errorMessage = error.response.data.message;
        } else if (error.response.data.error) {
          errorMessage = error.response.data.error;
        } else if (typeof error.response.data === 'string') {
          errorMessage = error.response.data;
        }
      } else if (error.message) {
        // Network errors or other axios errors
        if (error.message.includes('Network Error')) {
          errorMessage = 'Network error. Please check your internet connection.';
        } else if (error.message.includes('timeout')) {
          errorMessage = 'Request timeout. Please try again.';
        } else {
          errorMessage = error.message;
        }
      }

      console.error('🔴 [authSlice] Returning error message:', errorMessage);
      return rejectWithValue(errorMessage);
    }
  }
);

export const refreshToken = createAsyncThunk(
  'auth/refreshToken',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState();
      const refreshToken = state.auth.tokens?.refreshToken;
      
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }
      
      const response = await authService.refreshToken(refreshToken);
      
      // Store new tokens securely
      await secureStorage.setTokens(response);
      
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Token refresh failed');
    }
  }
);

export const getCurrentUser = createAsyncThunk(
  'auth/getCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const response = await authService.getCurrentUser();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to get user data');
    }
  }
);

export const logoutUser = createAsyncThunk(
  'auth/logoutUser',
  async (_, { rejectWithValue }) => {
    try {
      await authService.logout();
      await secureStorage.clearTokens();
      return null;
    } catch (error) {
      // Even if logout fails on server, clear local data
      await secureStorage.clearTokens();
      return null;
    }
  }
);

export const switchUserRole = createAsyncThunk(
  'auth/switchUserRole',
  async (newRole, { rejectWithValue }) => {
    try {
      await authService.switchRole(newRole);
      const updatedUser = await authService.getCurrentUser();
      return updatedUser;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Role switch failed');
    }
  }
);

export const verifyEmail = createAsyncThunk(
  'auth/verifyEmail',
  async (token, { rejectWithValue }) => {
    try {
      await authService.verifyEmail(token);
      const updatedUser = await authService.getCurrentUser();
      return updatedUser;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Email verification failed');
    }
  }
);

export const requestPasswordReset = createAsyncThunk(
  'auth/requestPasswordReset',
  async (email, { rejectWithValue }) => {
    try {
      await authService.requestPasswordReset(email);
      return { message: 'Password reset email sent' };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Password reset request failed');
    }
  }
);

export const resetPassword = createAsyncThunk(
  'auth/resetPassword',
  async ({ token, newPassword }, { rejectWithValue }) => {
    try {
      await authService.resetPassword(token, newPassword);
      return { message: 'Password reset successfully' };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Password reset failed');
    }
  }
);

export const updateProfile = createAsyncThunk(
  'auth/updateProfile',
  async (profileData, { rejectWithValue }) => {
    try {
      await authService.updateProfile(profileData);
      // Get the updated user data after profile update
      const updatedUser = await authService.getCurrentUser();
      return updatedUser;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Profile update failed');
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    hydrate: (state, action) => {
      state.user = action.payload.user;
      state.tokens = action.payload.tokens;
      state.isAuthenticated = true;
      state.isLoading = false;
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.tokens = action.payload.tokens;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
        state.isAuthenticated = false;
      })
      
      // Register
      .addCase(registerUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.error = null;
        // Clear any existing auth state after registration
        state.user = null;
        state.tokens = null;
        state.isAuthenticated = false;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      
      // Refresh Token
      .addCase(refreshToken.fulfilled, (state, action) => {
        state.tokens = action.payload;
      })
      .addCase(refreshToken.rejected, (state) => {
        state.user = null;
        state.tokens = null;
        state.isAuthenticated = false;
      })
      
      // Get Current User
      .addCase(getCurrentUser.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(getCurrentUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(getCurrentUser.rejected, (state) => {
        state.isLoading = false;
        state.user = null;
        state.isAuthenticated = false;
      })
      
      // Logout
      .addCase(logoutUser.fulfilled, (state) => {
        state.user = null;
        state.tokens = null;
        state.isAuthenticated = false;
        state.isLoading = false;
        state.error = null;
      })
      
      // Switch Role
      .addCase(switchUserRole.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(switchUserRole.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.error = null;
      })
      .addCase(switchUserRole.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      
      // Verify Email
      .addCase(verifyEmail.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(verifyEmail.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.error = null;
      })
      .addCase(verifyEmail.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      
      // Password Reset Request
      .addCase(requestPasswordReset.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(requestPasswordReset.fulfilled, (state) => {
        state.isLoading = false;
        state.error = null;
      })
      .addCase(requestPasswordReset.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      
      // Reset Password
      .addCase(resetPassword.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(resetPassword.fulfilled, (state) => {
        state.isLoading = false;
        state.error = null;
      })
      .addCase(resetPassword.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Update Profile
      .addCase(updateProfile.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(updateProfile.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.error = null;
      })
      .addCase(updateProfile.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });
  },
});

export const { clearError, setLoading, hydrate } = authSlice.actions;
export default authSlice.reducer;