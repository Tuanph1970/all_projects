import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { problemService } from '../../services/problemService';

// Async thunks for problem management
export const submitProblem = createAsyncThunk(
  'problem/submitProblem',
  async ({ imageUri, category, description }, { rejectWithValue }) => {
    try {
      const response = await problemService.submitProblem({
        imageUri,
        category,
        description
      });
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to submit problem');
    }
  }
);

export const fetchUserProblems = createAsyncThunk(
  'problem/fetchUserProblems',
  async ({ page = 1, limit = 10, category, status }, { rejectWithValue }) => {
    try {
      const response = await problemService.getUserProblems({
        page,
        limit,
        category,
        status
      });
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to fetch problems');
    }
  }
);

export const fetchProblemById = createAsyncThunk(
  'problem/fetchProblemById',
  async (problemId, { rejectWithValue }) => {
    try {
      const response = await problemService.getProblemById(problemId);
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to fetch problem');
    }
  }
);

export const deleteProblem = createAsyncThunk(
  'problem/deleteProblem',
  async (problemId, { rejectWithValue }) => {
    try {
      await problemService.deleteProblem(problemId);
      return problemId;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to delete problem');
    }
  }
);

// Initial state
const initialState = {
  problems: [],
  currentProblem: null,
  isLoading: false,
  isSubmitting: false,
  error: null,
  pagination: {
    currentPage: 1,
    totalPages: 1,
    totalItems: 0,
    hasNextPage: false,
    hasPreviousPage: false
  },
  filters: {
    category: null,
    status: null,
    searchQuery: ''
  },
  recentProblems: []
};

// Problem slice
const problemSlice = createSlice({
  name: 'problem',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentProblem: (state) => {
      state.currentProblem = null;
    },
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = {
        category: null,
        status: null,
        searchQuery: ''
      };
    },
    setSearchQuery: (state, action) => {
      state.filters.searchQuery = action.payload;
    },
    addToRecentProblems: (state, action) => {
      const problem = action.payload;
      // Remove if already exists
      state.recentProblems = state.recentProblems.filter(p => p.id !== problem.id);
      // Add to beginning and limit to 10
      state.recentProblems = [problem, ...state.recentProblems].slice(0, 10);
    },
    clearRecentProblems: (state) => {
      state.recentProblems = [];
    }
  },
  extraReducers: (builder) => {
    builder
      // Submit Problem
      .addCase(submitProblem.pending, (state) => {
        state.isSubmitting = true;
        state.error = null;
      })
      .addCase(submitProblem.fulfilled, (state, action) => {
        state.isSubmitting = false;
        state.currentProblem = action.payload;
        // Add to problems list if it exists
        if (state.problems.length > 0) {
          state.problems = [action.payload, ...state.problems];
        }
        // Add to recent problems
        state.recentProblems = [action.payload, ...state.recentProblems].slice(0, 10);
      })
      .addCase(submitProblem.rejected, (state, action) => {
        state.isSubmitting = false;
        state.error = action.payload;
      })
      // Fetch User Problems
      .addCase(fetchUserProblems.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchUserProblems.fulfilled, (state, action) => {
        state.isLoading = false;
        const { data, pagination } = action.payload;
        
        if (pagination.currentPage === 1) {
          // First page - replace data
          state.problems = data;
        } else {
          // Subsequent pages - append data
          state.problems = [...state.problems, ...data];
        }
        
        state.pagination = pagination;
      })
      .addCase(fetchUserProblems.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Fetch Problem By ID
      .addCase(fetchProblemById.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchProblemById.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentProblem = action.payload;
        // Add to recent problems
        state.recentProblems = [action.payload, ...state.recentProblems.filter(p => p.id !== action.payload.id)].slice(0, 10);
      })
      .addCase(fetchProblemById.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Delete Problem
      .addCase(deleteProblem.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(deleteProblem.fulfilled, (state, action) => {
        state.isLoading = false;
        const problemId = action.payload;
        // Remove from problems list
        state.problems = state.problems.filter(p => p.id !== problemId);
        // Remove from recent problems
        state.recentProblems = state.recentProblems.filter(p => p.id !== problemId);
        // Clear current problem if it's the deleted one
        if (state.currentProblem && state.currentProblem.id === problemId) {
          state.currentProblem = null;
        }
      })
      .addCase(deleteProblem.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });
  }
});

export const {
  clearError,
  clearCurrentProblem,
  setFilters,
  clearFilters,
  setSearchQuery,
  addToRecentProblems,
  clearRecentProblems
} = problemSlice.actions;

export default problemSlice.reducer;