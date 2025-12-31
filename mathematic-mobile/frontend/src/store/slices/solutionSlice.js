import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { solutionService } from '../../services/solutionService';

// Async thunks for solution management
export const fetchSolutionByProblemId = createAsyncThunk(
  'solution/fetchSolutionByProblemId',
  async (problemId, { rejectWithValue }) => {
    try {
      const response = await solutionService.getSolutionByProblemId(problemId);
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to fetch solution');
    }
  }
);

export const rateSolution = createAsyncThunk(
  'solution/rateSolution',
  async ({ solutionId, rating, feedback }, { rejectWithValue }) => {
    try {
      const response = await solutionService.rateSolution(solutionId, rating, feedback);
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to rate solution');
    }
  }
);

export const requestHint = createAsyncThunk(
  'solution/requestHint',
  async ({ problemId, currentStep }, { rejectWithValue }) => {
    try {
      const response = await solutionService.requestHint(problemId, currentStep);
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to get hint');
    }
  }
);

export const requestExplanation = createAsyncThunk(
  'solution/requestExplanation',
  async ({ solutionId, stepIndex }, { rejectWithValue }) => {
    try {
      const response = await solutionService.requestExplanation(solutionId, stepIndex);
      return response;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to get explanation');
    }
  }
);

// Initial state
const initialState = {
  currentSolution: null,
  isLoading: false,
  error: null,
  hints: [],
  explanations: {},
  userRating: null,
  isRatingSubmitted: false,
  currentStep: 0,
  showHints: false,
  solutionHistory: []
};

// Solution slice
const solutionSlice = createSlice({
  name: 'solution',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentSolution: (state) => {
      state.currentSolution = null;
      state.hints = [];
      state.explanations = {};
      state.userRating = null;
      state.isRatingSubmitted = false;
      state.currentStep = 0;
    },
    setCurrentStep: (state, action) => {
      state.currentStep = Math.max(0, Math.min(action.payload, state.currentSolution?.steps?.length - 1 || 0));
    },
    nextStep: (state) => {
      if (state.currentSolution && state.currentStep < state.currentSolution.steps.length - 1) {
        state.currentStep += 1;
      }
    },
    previousStep: (state) => {
      if (state.currentStep > 0) {
        state.currentStep -= 1;
      }
    },
    toggleHints: (state) => {
      state.showHints = !state.showHints;
    },
    setShowHints: (state, action) => {
      state.showHints = action.payload;
    },
    addToSolutionHistory: (state, action) => {
      const solution = action.payload;
      // Remove if already exists
      state.solutionHistory = state.solutionHistory.filter(s => s.id !== solution.id);
      // Add to beginning and limit to 20
      state.solutionHistory = [solution, ...state.solutionHistory].slice(0, 20);
    },
    clearSolutionHistory: (state) => {
      state.solutionHistory = [];
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch Solution
      .addCase(fetchSolutionByProblemId.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchSolutionByProblemId.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentSolution = action.payload;
        state.currentStep = 0;
        // Add to solution history
        state.solutionHistory = [action.payload, ...state.solutionHistory.filter(s => s.id !== action.payload.id)].slice(0, 20);
      })
      .addCase(fetchSolutionByProblemId.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Rate Solution
      .addCase(rateSolution.pending, (state) => {
        state.error = null;
      })
      .addCase(rateSolution.fulfilled, (state, action) => {
        state.userRating = action.payload.rating;
        state.isRatingSubmitted = true;
        // Update current solution if available
        if (state.currentSolution) {
          state.currentSolution.userRating = action.payload.rating;
          state.currentSolution.userFeedback = action.payload.feedback;
        }
      })
      .addCase(rateSolution.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Request Hint
      .addCase(requestHint.pending, (state) => {
        state.error = null;
      })
      .addCase(requestHint.fulfilled, (state, action) => {
        const hint = action.payload;
        // Add hint if not already exists
        if (!state.hints.find(h => h.stepIndex === hint.stepIndex)) {
          state.hints.push(hint);
        }
      })
      .addCase(requestHint.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Request Explanation
      .addCase(requestExplanation.pending, (state) => {
        state.error = null;
      })
      .addCase(requestExplanation.fulfilled, (state, action) => {
        const { stepIndex, explanation } = action.payload;
        state.explanations[stepIndex] = explanation;
      })
      .addCase(requestExplanation.rejected, (state, action) => {
        state.error = action.payload;
      });
  }
});

export const {
  clearError,
  clearCurrentSolution,
  setCurrentStep,
  nextStep,
  previousStep,
  toggleHints,
  setShowHints,
  addToSolutionHistory,
  clearSolutionHistory
} = solutionSlice.actions;

export default solutionSlice.reducer;