/**
 * Unit tests for authSlice Redux reducer and thunks
 */

// Mock authService BEFORE importing slice
jest.mock('../../src/services/authService', () => ({
  authService: {
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn(),
  }
}));

// Mock expo-secure-store
jest.mock('expo-secure-store', () => ({
  setItemAsync: jest.fn(),
  getItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

const { configureStore } = require('@reduxjs/toolkit');
const authReducer = require('../../src/store/slices/authSlice').default;
const {
  clearError,
  clearAuth,
  updateLastActivity,
  setAuthFromStorage,
  initializeAuth,
  loginUser,
  registerUser,
  logoutUser,
  refreshToken,
} = require('../../src/store/slices/authSlice');
const { authService } = require('../../src/services/authService');

// ──────────────────────────────────────────────────────────────
// Store factory
// ──────────────────────────────────────────────────────────────
function createStore() {
  return configureStore({ reducer: { auth: authReducer } });
}

const initialState = {
  user: null,
  token: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  lastActivity: null,
  isInitialized: false,
};

// ──────────────────────────────────────────────────────────────
// Tests
// ──────────────────────────────────────────────────────────────

describe('authSlice', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── Initial state ─────────────────────────────────────────────

  describe('initial state', () => {
    it('has correct initial state', () => {
      const state = authReducer(undefined, { type: '@@INIT' });
      expect(state).toEqual(initialState);
    });
  });

  // ── Synchronous reducers ──────────────────────────────────────

  describe('clearError', () => {
    it('clears error field', () => {
      const stateWithError = { ...initialState, error: 'Login failed' };
      const result = authReducer(stateWithError, clearError());
      expect(result.error).toBeNull();
    });
  });

  describe('clearAuth', () => {
    it('resets user, token, refreshToken and isAuthenticated', () => {
      const authenticatedState = {
        ...initialState,
        user: { id: '1', username: 'john' },
        token: 'access_token',
        refreshToken: 'refresh_token',
        isAuthenticated: true,
        error: 'some error',
      };
      const result = authReducer(authenticatedState, clearAuth());
      expect(result.user).toBeNull();
      expect(result.token).toBeNull();
      expect(result.refreshToken).toBeNull();
      expect(result.isAuthenticated).toBe(false);
      expect(result.error).toBeNull();
    });
  });

  describe('updateLastActivity', () => {
    it('sets lastActivity to current timestamp', () => {
      const before = Date.now();
      const result = authReducer(initialState, updateLastActivity());
      expect(result.lastActivity).toBeGreaterThanOrEqual(before);
    });
  });

  describe('setAuthFromStorage', () => {
    it('sets user and token from payload, isAuthenticated=true when token present', () => {
      const payload = { user: { id: '1' }, token: 'tok', refreshToken: 'rtok' };
      const result = authReducer(initialState, setAuthFromStorage(payload));
      expect(result.user).toEqual({ id: '1' });
      expect(result.token).toBe('tok');
      expect(result.refreshToken).toBe('rtok');
      expect(result.isAuthenticated).toBe(true);
      expect(result.isInitialized).toBe(true);
    });

    it('sets isAuthenticated=false when token is null', () => {
      const payload = { user: null, token: null, refreshToken: null };
      const result = authReducer(initialState, setAuthFromStorage(payload));
      expect(result.isAuthenticated).toBe(false);
      expect(result.isInitialized).toBe(true);
    });
  });

  describe('initializeAuth', () => {
    it('sets isInitialized=true and isLoading=false', () => {
      const loadingState = { ...initialState, isLoading: true };
      const result = authReducer(loadingState, initializeAuth());
      expect(result.isInitialized).toBe(true);
      expect(result.isLoading).toBe(false);
    });
  });

  // ── loginUser thunk ───────────────────────────────────────────

  describe('loginUser', () => {
    const mockAuthData = {
      user: { id: '1', username: 'testuser' },
      token: 'access_token',
      refreshToken: 'refresh_token',
    };

    it('pending: sets isLoading=true and clears error', () => {
      const store = createStore();
      store.dispatch({ type: loginUser.pending.type });
      const { auth } = store.getState();
      expect(auth.isLoading).toBe(true);
      expect(auth.error).toBeNull();
    });

    it('fulfilled: sets user, token, refreshToken, isAuthenticated=true', () => {
      const store = createStore();
      store.dispatch({ type: loginUser.fulfilled.type, payload: mockAuthData });
      const { auth } = store.getState();
      expect(auth.isLoading).toBe(false);
      expect(auth.user).toEqual(mockAuthData.user);
      expect(auth.token).toBe('access_token');
      expect(auth.refreshToken).toBe('refresh_token');
      expect(auth.isAuthenticated).toBe(true);
      expect(auth.error).toBeNull();
    });

    it('rejected: sets error and isAuthenticated=false', () => {
      const store = createStore();
      store.dispatch({ type: loginUser.rejected.type, payload: 'Invalid credentials' });
      const { auth } = store.getState();
      expect(auth.isLoading).toBe(false);
      expect(auth.error).toBe('Invalid credentials');
      expect(auth.isAuthenticated).toBe(false);
    });

    it('calls authService.login with correct args', async () => {
      authService.login.mockResolvedValueOnce(mockAuthData);
      const store = createStore();
      await store.dispatch(loginUser({ username: 'testuser', password: 'pass123' }));
      expect(authService.login).toHaveBeenCalledWith('testuser', 'pass123');
    });

    it('dispatches rejected on service error', async () => {
      authService.login.mockRejectedValueOnce(new Error('Network error'));
      const store = createStore();
      await store.dispatch(loginUser({ username: 'u', password: 'p' }));
      const { auth } = store.getState();
      expect(auth.isAuthenticated).toBe(false);
      expect(auth.error).toBeTruthy();
    });
  });

  // ── registerUser thunk ────────────────────────────────────────

  describe('registerUser', () => {
    const mockRegData = {
      user: { id: '2', username: 'newuser' },
      token: 'new_token',
      refreshToken: 'new_refresh',
    };

    it('pending: sets isLoading=true', () => {
      const store = createStore();
      store.dispatch({ type: registerUser.pending.type });
      expect(store.getState().auth.isLoading).toBe(true);
    });

    it('fulfilled: sets user and isAuthenticated=true', () => {
      const store = createStore();
      store.dispatch({ type: registerUser.fulfilled.type, payload: mockRegData });
      const { auth } = store.getState();
      expect(auth.isAuthenticated).toBe(true);
      expect(auth.user).toEqual(mockRegData.user);
      expect(auth.token).toBe('new_token');
    });

    it('rejected: sets error and isAuthenticated=false', () => {
      const store = createStore();
      store.dispatch({ type: registerUser.rejected.type, payload: 'Username taken' });
      const { auth } = store.getState();
      expect(auth.error).toBe('Username taken');
      expect(auth.isAuthenticated).toBe(false);
    });
  });

  // ── logoutUser thunk ──────────────────────────────────────────

  describe('logoutUser', () => {
    const loggedInState = {
      ...initialState,
      user: { id: '1', username: 'testuser' },
      token: 'access_token',
      refreshToken: 'refresh_token',
      isAuthenticated: true,
    };

    it('fulfilled: clears user, token, refreshToken and sets isAuthenticated=false', () => {
      const store = configureStore({
        reducer: { auth: authReducer },
        preloadedState: { auth: loggedInState },
      });
      store.dispatch({ type: logoutUser.fulfilled.type });
      const { auth } = store.getState();
      expect(auth.user).toBeNull();
      expect(auth.token).toBeNull();
      expect(auth.refreshToken).toBeNull();
      expect(auth.isAuthenticated).toBe(false);
    });

    it('rejected: still clears auth data', () => {
      const store = configureStore({
        reducer: { auth: authReducer },
        preloadedState: { auth: loggedInState },
      });
      store.dispatch({ type: logoutUser.rejected.type, payload: 'Logout failed' });
      const { auth } = store.getState();
      expect(auth.user).toBeNull();
      expect(auth.isAuthenticated).toBe(false);
    });
  });

  // ── refreshToken thunk ────────────────────────────────────────

  describe('refreshToken', () => {
    it('fulfilled: updates token and refreshToken', () => {
      const store = configureStore({
        reducer: { auth: authReducer },
        preloadedState: {
          auth: { ...initialState, token: 'old_token', refreshToken: 'old_refresh' },
        },
      });
      store.dispatch({
        type: refreshToken.fulfilled.type,
        payload: { token: 'new_token', refreshToken: 'new_refresh' },
      });
      const { auth } = store.getState();
      expect(auth.token).toBe('new_token');
      expect(auth.refreshToken).toBe('new_refresh');
    });

    it('rejected: clears auth data', () => {
      const loggedInAuth = {
        ...initialState,
        token: 'expired_token',
        refreshToken: 'expired_refresh',
        isAuthenticated: true,
        user: { id: '1' },
      };
      const store = configureStore({
        reducer: { auth: authReducer },
        preloadedState: { auth: loggedInAuth },
      });
      store.dispatch({ type: refreshToken.rejected.type, payload: 'Refresh failed' });
      const { auth } = store.getState();
      expect(auth.token).toBeNull();
      expect(auth.isAuthenticated).toBe(false);
    });
  });
});
