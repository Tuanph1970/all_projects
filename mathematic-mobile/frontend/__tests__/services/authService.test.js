/**
 * Unit tests for AuthService
 */

// Mock dependencies before requiring the module
jest.mock('../../src/services/apiClient', () => {
  const mockPost = jest.fn();
  const mockGet = jest.fn();
  return {
    __esModule: true,
    default: { post: mockPost, get: mockGet },
    handleApiResponse: jest.fn((response) => response.data),
    handleApiError: jest.fn((error) => { throw error; }),
  };
});

jest.mock('expo-secure-store', () => ({
  setItemAsync: jest.fn().mockResolvedValue(undefined),
  getItemAsync: jest.fn().mockResolvedValue(null),
  deleteItemAsync: jest.fn().mockResolvedValue(undefined),
}));

const SecureStore = require('expo-secure-store');
const apiClientModule = require('../../src/services/apiClient');
const apiClient = apiClientModule.default;
const { handleApiResponse, handleApiError } = apiClientModule;

// Re-require to pick up the mocks
const { authService } = require('../../src/services/authService');

describe('AuthService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default: handleApiResponse returns the data property
    handleApiResponse.mockImplementation((r) => r.data);
  });

  // ── login ─────────────────────────────────────────────────────

  describe('login()', () => {
    const mockResponse = {
      data: { token: 'access_tok', refreshToken: 'refresh_tok', user: { id: '1' } }
    };

    it('calls POST /auth/login with usernameOrEmail and password', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      await authService.login('testuser', 'pass123');

      expect(apiClient.post).toHaveBeenCalledWith(
        '/auth/login',
        { usernameOrEmail: 'testuser', password: 'pass123' }
      );
    });

    it('stores access token in SecureStore', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      await authService.login('testuser', 'pass123');

      expect(SecureStore.setItemAsync).toHaveBeenCalledWith('authToken', 'access_tok');
    });

    it('stores refresh token in SecureStore', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      await authService.login('testuser', 'pass123');

      expect(SecureStore.setItemAsync).toHaveBeenCalledWith('refreshToken', 'refresh_tok');
    });

    it('returns the response data', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      const result = await authService.login('testuser', 'pass123');

      expect(result).toEqual(mockResponse.data);
    });
  });

  // ── register ──────────────────────────────────────────────────

  describe('register()', () => {
    const mockResponse = {
      data: { token: 'new_token', refreshToken: 'new_refresh', user: { id: '2' } }
    };

    it('calls POST /auth/register with correct body', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      await authService.register('newuser', 'new@test.com', 'pass123');

      expect(apiClient.post).toHaveBeenCalledWith(
        '/auth/register',
        expect.objectContaining({
          username: 'newuser',
          email: 'new@test.com',
          password: 'pass123',
        })
      );
    });

    it('stores tokens in SecureStore on success', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      await authService.register('newuser', 'new@test.com', 'pass123');

      expect(SecureStore.setItemAsync).toHaveBeenCalledWith('authToken', 'new_token');
      expect(SecureStore.setItemAsync).toHaveBeenCalledWith('refreshToken', 'new_refresh');
    });
  });

  // ── logout ────────────────────────────────────────────────────

  describe('logout()', () => {
    it('calls POST /auth/logout', async () => {
      SecureStore.getItemAsync.mockResolvedValueOnce('some_refresh_token');
      apiClient.post.mockResolvedValueOnce({ data: { success: true } });

      await authService.logout();

      expect(apiClient.post).toHaveBeenCalledWith(
        '/auth/logout',
        expect.objectContaining({ refreshToken: 'some_refresh_token' })
      );
    });

    it('always clears tokens even if server call fails', async () => {
      SecureStore.getItemAsync.mockResolvedValueOnce('token');
      apiClient.post.mockRejectedValueOnce(new Error('Network error'));

      await authService.logout();

      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('authToken');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('refreshToken');
    });

    it('clears tokens on successful logout', async () => {
      SecureStore.getItemAsync.mockResolvedValueOnce('token');
      apiClient.post.mockResolvedValueOnce({ data: {} });

      await authService.logout();

      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('authToken');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('refreshToken');
    });
  });

  // ── refreshToken ──────────────────────────────────────────────

  describe('refreshToken()', () => {
    it('gets refresh token from SecureStore before calling endpoint', async () => {
      SecureStore.getItemAsync
        .mockResolvedValueOnce('current_access') // authToken
        .mockResolvedValueOnce('current_refresh'); // refreshToken
      apiClient.post.mockResolvedValueOnce({
        data: { token: 'new_tok', refreshToken: 'new_ref' }
      });

      await authService.refreshToken();

      expect(SecureStore.getItemAsync).toHaveBeenCalledWith('authToken');
      expect(SecureStore.getItemAsync).toHaveBeenCalledWith('refreshToken');
    });

    it('calls POST /auth/refresh with tokens', async () => {
      SecureStore.getItemAsync
        .mockResolvedValueOnce('current_access')
        .mockResolvedValueOnce('current_refresh');
      apiClient.post.mockResolvedValueOnce({
        data: { token: 'new_tok', refreshToken: 'new_ref' }
      });

      await authService.refreshToken();

      expect(apiClient.post).toHaveBeenCalledWith('/auth/refresh', {
        token: 'current_access',
        refreshToken: 'current_refresh',
      });
    });

    it('stores new tokens in SecureStore', async () => {
      SecureStore.getItemAsync
        .mockResolvedValueOnce('old_access')
        .mockResolvedValueOnce('old_refresh');
      apiClient.post.mockResolvedValueOnce({
        data: { token: 'fresh_token', refreshToken: 'fresh_refresh' }
      });

      await authService.refreshToken();

      expect(SecureStore.setItemAsync).toHaveBeenCalledWith('authToken', 'fresh_token');
      expect(SecureStore.setItemAsync).toHaveBeenCalledWith('refreshToken', 'fresh_refresh');
    });
  });

  // ── getStoredTokens ───────────────────────────────────────────

  describe('getStoredTokens()', () => {
    it('returns both tokens from SecureStore', async () => {
      SecureStore.getItemAsync
        .mockResolvedValueOnce('my_auth_token')
        .mockResolvedValueOnce('my_refresh_token');

      const tokens = await authService.getStoredTokens();

      expect(tokens.authToken).toBe('my_auth_token');
      expect(tokens.refreshToken).toBe('my_refresh_token');
    });

    it('returns null values when SecureStore throws', async () => {
      SecureStore.getItemAsync.mockRejectedValueOnce(new Error('SecureStore unavailable'));

      const tokens = await authService.getStoredTokens();

      expect(tokens.authToken).toBeNull();
      expect(tokens.refreshToken).toBeNull();
    });
  });

  // ── clearTokens ───────────────────────────────────────────────

  describe('clearTokens()', () => {
    it('deletes both authToken and refreshToken from SecureStore', async () => {
      await authService.clearTokens();

      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('authToken');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('refreshToken');
    });
  });

  // ── isAuthenticated ───────────────────────────────────────────

  describe('isAuthenticated()', () => {
    it('returns true when authToken exists', async () => {
      SecureStore.getItemAsync.mockResolvedValueOnce('some_token');

      const result = await authService.isAuthenticated();

      expect(result).toBe(true);
    });

    it('returns false when no authToken', async () => {
      SecureStore.getItemAsync
        .mockResolvedValueOnce(null)   // authToken
        .mockResolvedValueOnce(null);  // refreshToken

      const result = await authService.isAuthenticated();

      expect(result).toBe(false);
    });
  });
});
