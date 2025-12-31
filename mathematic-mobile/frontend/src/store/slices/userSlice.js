import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { userService } from '../../services/userService';

// Async thunks for user management
export const fetchUserProfile = createAsyncThunk(
  'user/fetchUserProfile',
  async (_, { rejectWithValue }) => {
    try {
      const response = await userService.getUserProfile();
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to fetch user profile');
    }
  }
);

export const updateUserProfile = createAsyncThunk(
  'user/updateUserProfile',
  async (profileData, { rejectWithValue }) => {
    try {
      const response = await userService.updateUserProfile(profileData);
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to update profile');
    }
  }
);

export const changePassword = createAsyncThunk(
  'user/changePassword',
  async ({ currentPassword, newPassword }, { rejectWithValue }) => {
    try {
      const response = await userService.changePassword(currentPassword, newPassword);
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to change password');
    }
  }
);

export const fetchUserStats = createAsyncThunk(
  'user/fetchUserStats',
  async (_, { rejectWithValue }) => {
    try {
      const response = await userService.getUserStats();
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to fetch user stats');
    }
  }
);

export const updateUserPreferences = createAsyncThunk(
  'user/updateUserPreferences',
  async (preferences, { rejectWithValue }) => {
    try {
      const response = await userService.updateUserPreferences(preferences);
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to update preferences');
    }
  }
);

// Initial state
const initialState = {
  profile: null,
  stats: {
    totalProblems: 0,
    solvedProblems: 0,
    averageRating: 0,
    totalPoints: 0,
    streak: 0,
    rank: null,
    achievements: []
  },
  preferences: {
    theme: 'light',
    notifications: {
      push: true,
      email: false,
      solutionReady: true,
      weeklyReport: true
    },
    language: 'en',
    mathNotation: 'latex',
    hintLevel: 'medium'
  },
  isLoading: false,
  isUpdating: false,
  error: null,
  lastProfileUpdate: null
};

// User slice
const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearUserData: (state) => {
      state.profile = null;
      state.stats = {
        totalProblems: 0,
        solvedProblems: 0,
        averageRating: 0,
        totalPoints: 0,
        streak: 0,
        rank: null,
        achievements: []
      };
      state.error = null;
      state.lastProfileUpdate = null;
    },
    updateLocalPreferences: (state, action) => {
      state.preferences = { ...state.preferences, ...action.payload };
    },
    updateLocalStats: (state, action) => {
      state.stats = { ...state.stats, ...action.payload };
    },
    incrementProblemCount: (state) => {
      state.stats.totalProblems += 1;
    },
    incrementSolvedCount: (state) => {
      state.stats.solvedProblems += 1;
    },
    updateStreak: (state, action) => {
      state.stats.streak = action.payload;
    },
    addAchievement: (state, action) => {
      const achievement = action.payload;
      if (!state.stats.achievements.find(a => a.id === achievement.id)) {
        state.stats.achievements.push(achievement);
      }
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch User Profile
      .addCase(fetchUserProfile.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchUserProfile.fulfilled, (state, action) => {
        state.isLoading = false;
        state.profile = action.payload;
        state.lastProfileUpdate = Date.now();
      })
      .addCase(fetchUserProfile.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Update User Profile
      .addCase(updateUserProfile.pending, (state) => {
        state.isUpdating = true;
        state.error = null;
      })
      .addCase(updateUserProfile.fulfilled, (state, action) => {
        state.isUpdating = false;
        state.profile = { ...state.profile, ...action.payload };
        state.lastProfileUpdate = Date.now();
      })
      .addCase(updateUserProfile.rejected, (state, action) => {
        state.isUpdating = false;
        state.error = action.payload;
      })
      // Change Password
      .addCase(changePassword.pending, (state) => {
        state.isUpdating = true;
        state.error = null;
      })
      .addCase(changePassword.fulfilled, (state) => {
        state.isUpdating = false;
        // Password change successful - no state changes needed
      })
      .addCase(changePassword.rejected, (state, action) => {
        state.isUpdating = false;
        state.error = action.payload;
      })
      // Fetch User Stats
      .addCase(fetchUserStats.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchUserStats.fulfilled, (state, action) => {
        state.isLoading = false;
        state.stats = { ...state.stats, ...action.payload };
      })
      .addCase(fetchUserStats.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Update User Preferences
      .addCase(updateUserPreferences.pending, (state) => {
        state.isUpdating = true;
        state.error = null;
      })
      .addCase(updateUserPreferences.fulfilled, (state, action) => {
        state.isUpdating = false;
        state.preferences = { ...state.preferences, ...action.payload };
      })
      .addCase(updateUserPreferences.rejected, (state, action) => {
        state.isUpdating = false;
        state.error = action.payload;
      });
  }
});

export const {
  clearError,
  clearUserData,
  updateLocalPreferences,
  updateLocalStats,
  incrementProblemCount,
  incrementSolvedCount,
  updateStreak,
  addAchievement
} = userSlice.actions;

export default userSlice.reducer;