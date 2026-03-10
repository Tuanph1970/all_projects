/**
 * Unit tests for problemSlice Redux reducer and thunks
 */

jest.mock('../../src/services/problemService', () => ({
  problemService: {
    submitProblem: jest.fn(),
    getUserProblems: jest.fn(),
    getProblemById: jest.fn(),
    deleteProblem: jest.fn(),
  }
}));

const { configureStore } = require('@reduxjs/toolkit');
const problemReducer = require('../../src/store/slices/problemSlice').default;
const {
  clearError,
  clearCurrentProblem,
  setFilters,
  clearFilters,
  setSearchQuery,
  addToRecentProblems,
  clearRecentProblems,
  submitProblem,
  fetchUserProblems,
  fetchProblemById,
  deleteProblem,
} = require('../../src/store/slices/problemSlice');

function createStore(preloadedState) {
  return configureStore({
    reducer: { problem: problemReducer },
    preloadedState,
  });
}

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
    hasPreviousPage: false,
  },
  filters: {
    category: null,
    status: null,
    searchQuery: '',
  },
  recentProblems: [],
};

const mockProblem = { id: 'p1', title: 'Solve x', category: 'Algebra', status: 'Pending' };
const mockProblem2 = { id: 'p2', title: 'Integrate f(x)', category: 'Calculus', status: 'Completed' };

describe('problemSlice', () => {
  beforeEach(() => jest.clearAllMocks());

  // ── Initial state ─────────────────────────────────────────────

  it('has correct initial state', () => {
    const state = problemReducer(undefined, { type: '@@INIT' });
    expect(state).toEqual(initialState);
  });

  // ── Synchronous reducers ──────────────────────────────────────

  describe('clearError', () => {
    it('clears error', () => {
      const s = { ...initialState, error: 'Something failed' };
      expect(problemReducer(s, clearError()).error).toBeNull();
    });
  });

  describe('clearCurrentProblem', () => {
    it('sets currentProblem to null', () => {
      const s = { ...initialState, currentProblem: mockProblem };
      expect(problemReducer(s, clearCurrentProblem()).currentProblem).toBeNull();
    });
  });

  describe('setFilters', () => {
    it('merges filters with existing state', () => {
      const result = problemReducer(initialState, setFilters({ category: 'Algebra' }));
      expect(result.filters.category).toBe('Algebra');
      expect(result.filters.status).toBeNull(); // unchanged
    });

    it('updates multiple filter fields at once', () => {
      const result = problemReducer(initialState, setFilters({ category: 'Geometry', status: 'Pending' }));
      expect(result.filters.category).toBe('Geometry');
      expect(result.filters.status).toBe('Pending');
    });
  });

  describe('clearFilters', () => {
    it('resets filters to defaults', () => {
      const s = { ...initialState, filters: { category: 'Algebra', status: 'Completed', searchQuery: 'x^2' } };
      const result = problemReducer(s, clearFilters());
      expect(result.filters).toEqual({ category: null, status: null, searchQuery: '' });
    });
  });

  describe('setSearchQuery', () => {
    it('updates searchQuery in filters', () => {
      const result = problemReducer(initialState, setSearchQuery('quadratic equation'));
      expect(result.filters.searchQuery).toBe('quadratic equation');
    });
  });

  describe('addToRecentProblems', () => {
    it('adds problem to front of recentProblems', () => {
      const result = problemReducer(initialState, addToRecentProblems(mockProblem));
      expect(result.recentProblems[0]).toEqual(mockProblem);
    });

    it('removes duplicate and re-adds to front', () => {
      const s = { ...initialState, recentProblems: [mockProblem, mockProblem2] };
      const result = problemReducer(s, addToRecentProblems(mockProblem2));
      expect(result.recentProblems[0]).toEqual(mockProblem2);
      expect(result.recentProblems).toHaveLength(2);
    });

    it('limits recentProblems to 10 items', () => {
      const tenProblems = Array.from({ length: 10 }, (_, i) => ({ id: `p${i}`, title: `P${i}` }));
      const s = { ...initialState, recentProblems: tenProblems };
      const newProblem = { id: 'p_new', title: 'New' };
      const result = problemReducer(s, addToRecentProblems(newProblem));
      expect(result.recentProblems).toHaveLength(10);
      expect(result.recentProblems[0]).toEqual(newProblem);
    });
  });

  describe('clearRecentProblems', () => {
    it('empties recentProblems array', () => {
      const s = { ...initialState, recentProblems: [mockProblem] };
      const result = problemReducer(s, clearRecentProblems());
      expect(result.recentProblems).toHaveLength(0);
    });
  });

  // ── submitProblem thunk ───────────────────────────────────────

  describe('submitProblem', () => {
    it('pending: sets isSubmitting=true and clears error', () => {
      const store = createStore();
      store.dispatch({ type: submitProblem.pending.type });
      const { problem } = store.getState();
      expect(problem.isSubmitting).toBe(true);
      expect(problem.error).toBeNull();
    });

    it('fulfilled: sets currentProblem and adds to problems list', () => {
      const store = createStore({ problem: { ...initialState, problems: [mockProblem2] } });
      store.dispatch({ type: submitProblem.fulfilled.type, payload: mockProblem });
      const { problem } = store.getState();
      expect(problem.isSubmitting).toBe(false);
      expect(problem.currentProblem).toEqual(mockProblem);
      expect(problem.problems[0]).toEqual(mockProblem); // prepended
    });

    it('fulfilled: adds to recentProblems', () => {
      const store = createStore();
      store.dispatch({ type: submitProblem.fulfilled.type, payload: mockProblem });
      expect(store.getState().problem.recentProblems[0]).toEqual(mockProblem);
    });

    it('rejected: sets error and isSubmitting=false', () => {
      const store = createStore();
      store.dispatch({ type: submitProblem.rejected.type, payload: 'Upload failed' });
      const { problem } = store.getState();
      expect(problem.isSubmitting).toBe(false);
      expect(problem.error).toBe('Upload failed');
    });
  });

  // ── fetchUserProblems thunk ───────────────────────────────────

  describe('fetchUserProblems', () => {
    const mockPaginatedResponse = {
      data: [mockProblem, mockProblem2],
      pagination: { currentPage: 1, totalPages: 2, totalItems: 20, hasNextPage: true, hasPreviousPage: false },
    };

    it('pending: sets isLoading=true', () => {
      const store = createStore();
      store.dispatch({ type: fetchUserProblems.pending.type });
      expect(store.getState().problem.isLoading).toBe(true);
    });

    it('fulfilled: replaces problems on page 1', () => {
      const store = createStore({ problem: { ...initialState, problems: [{ id: 'old' }] } });
      store.dispatch({ type: fetchUserProblems.fulfilled.type, payload: mockPaginatedResponse });
      const { problem } = store.getState();
      expect(problem.problems).toEqual([mockProblem, mockProblem2]);
      expect(problem.isLoading).toBe(false);
    });

    it('fulfilled: appends problems on page 2+', () => {
      const page2Response = {
        data: [{ id: 'p3', title: 'P3' }],
        pagination: { currentPage: 2, totalPages: 2, totalItems: 3, hasNextPage: false, hasPreviousPage: true },
      };
      const store = createStore({ problem: { ...initialState, problems: [mockProblem] } });
      store.dispatch({ type: fetchUserProblems.fulfilled.type, payload: page2Response });
      const { problem } = store.getState();
      expect(problem.problems).toHaveLength(2);
    });

    it('fulfilled: updates pagination', () => {
      const store = createStore();
      store.dispatch({ type: fetchUserProblems.fulfilled.type, payload: mockPaginatedResponse });
      const { problem } = store.getState();
      expect(problem.pagination.hasNextPage).toBe(true);
      expect(problem.pagination.totalItems).toBe(20);
    });

    it('rejected: sets error and isLoading=false', () => {
      const store = createStore();
      store.dispatch({ type: fetchUserProblems.rejected.type, payload: 'Network error' });
      const { problem } = store.getState();
      expect(problem.isLoading).toBe(false);
      expect(problem.error).toBe('Network error');
    });
  });

  // ── fetchProblemById thunk ────────────────────────────────────

  describe('fetchProblemById', () => {
    it('fulfilled: sets currentProblem and adds to recentProblems', () => {
      const store = createStore();
      store.dispatch({ type: fetchProblemById.fulfilled.type, payload: mockProblem });
      const { problem } = store.getState();
      expect(problem.currentProblem).toEqual(mockProblem);
      expect(problem.recentProblems[0]).toEqual(mockProblem);
    });

    it('fulfilled: moves existing problem to front of recentProblems', () => {
      const store = createStore({ problem: { ...initialState, recentProblems: [mockProblem2, mockProblem] } });
      store.dispatch({ type: fetchProblemById.fulfilled.type, payload: mockProblem });
      const { problem } = store.getState();
      expect(problem.recentProblems[0]).toEqual(mockProblem);
      expect(problem.recentProblems).toHaveLength(2);
    });
  });

  // ── deleteProblem thunk ───────────────────────────────────────

  describe('deleteProblem', () => {
    it('fulfilled: removes problem from problems list', () => {
      const store = createStore({ problem: { ...initialState, problems: [mockProblem, mockProblem2] } });
      store.dispatch({ type: deleteProblem.fulfilled.type, payload: 'p1' });
      const { problem } = store.getState();
      expect(problem.problems).not.toContainEqual(mockProblem);
      expect(problem.problems).toContainEqual(mockProblem2);
    });

    it('fulfilled: removes problem from recentProblems', () => {
      const store = createStore({ problem: { ...initialState, recentProblems: [mockProblem, mockProblem2] } });
      store.dispatch({ type: deleteProblem.fulfilled.type, payload: 'p1' });
      expect(store.getState().problem.recentProblems).not.toContainEqual(mockProblem);
    });

    it('fulfilled: clears currentProblem if it is the deleted one', () => {
      const store = createStore({ problem: { ...initialState, currentProblem: mockProblem } });
      store.dispatch({ type: deleteProblem.fulfilled.type, payload: 'p1' });
      expect(store.getState().problem.currentProblem).toBeNull();
    });

    it('fulfilled: does not clear currentProblem if it is a different problem', () => {
      const store = createStore({ problem: { ...initialState, currentProblem: mockProblem2 } });
      store.dispatch({ type: deleteProblem.fulfilled.type, payload: 'p1' });
      expect(store.getState().problem.currentProblem).toEqual(mockProblem2);
    });
  });
});
