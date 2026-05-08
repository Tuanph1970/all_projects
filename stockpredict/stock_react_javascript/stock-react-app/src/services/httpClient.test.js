/**
 * Tests for httpClient — covers the 401 → refresh → retry interceptor.
 *
 * Drives the response error handler directly rather than firing real
 * HTTP, so the test stays fast and deterministic. The factory in
 * `mockAxios` captures the interceptor handlers the module registers
 * during construction, then the test calls them with synthesized
 * `{config, response}` objects.
 *
 * Requires `transformIgnorePatterns: ['node_modules/(?!(axios)/)']`
 * in package.json's jest config so axios v1's ESM is transformed.
 */

// Don't auto-mock axios — that loses our manual mockReturnValue on
// jest.isolateModules. Instead each test does its own jest.doMock inside
// an isolated module scope so the singleton in httpClient.js sees the
// configured axios.create() at construction time.
let httpClient;
let lastAxiosPostMock;

const stubAxiosInstance = () => {
  const responseError = [];
  const instance = {
    interceptors: {
      request: { use: () => {} },
      response: { use: (_success, error) => { responseError.push(error); } },
    },
    request: jest.fn(),
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    patch: jest.fn(),
  };
  return { instance, responseError };
};

const importHttpClient = (instance, postImpl) => {
  jest.isolateModules(() => {
    const post = jest.fn();
    if (postImpl) post.mockImplementation(postImpl);
    jest.doMock('axios', () => ({
      __esModule: true,
      default: {
        create: jest.fn(() => instance),
        post,
      },
      create: jest.fn(() => instance),
      post,
    }));
    httpClient = require('./httpClient').default;
    lastAxiosPostMock = post;
  });
  return httpClient;
};

beforeEach(() => {
  jest.resetModules();
  jest.clearAllMocks();
  localStorage.clear();
});

describe('httpClient 401 refresh interceptor', () => {
  test('retries the original request with a new access token after a successful refresh', async () => {
    const stub = stubAxiosInstance();
    importHttpClient(stub.instance, () =>
      Promise.resolve({ data: { access_token: 'new-access' } })
    );

    localStorage.setItem('token', 'old-access');
    localStorage.setItem('refreshToken', 'refresh-1');

    const originalRequest = { url: '/anything', headers: {} };
    stub.instance.request.mockResolvedValue({ data: { ok: true } });

    const errorHandler = stub.responseError[0];
    const result = await errorHandler({
      config: originalRequest,
      response: { status: 401 },
    });

    expect(lastAxiosPostMock).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem('token')).toBe('new-access');
    expect(originalRequest.headers.Authorization).toBe('Bearer new-access');
    expect(result).toEqual({ data: { ok: true } });
  });

  test('clears auth storage when refresh fails', async () => {
    const stub = stubAxiosInstance();
    importHttpClient(stub.instance, () =>
      Promise.reject(new Error('refresh failed'))
    );

    localStorage.setItem('token', 'old-access');
    localStorage.setItem('refreshToken', 'refresh-1');
    localStorage.setItem('email', 'someone@example.com');

    const errorHandler = stub.responseError[0];
    await expect(
      errorHandler({
        config: { url: '/anything', headers: {} },
        response: { status: 401 },
      })
    ).rejects.toBeDefined();

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
    expect(localStorage.getItem('email')).toBeNull();
  });

  test('does not attempt refresh when the failing request is auth/refresh itself', async () => {
    const stub = stubAxiosInstance();
    importHttpClient(stub.instance);

    localStorage.setItem('refreshToken', 'refresh-1');

    // _isAuthEndpoint() does substring matching against the full
    // API_ENDPOINTS.AUTH_REFRESH URL, so the failing request needs to
    // contain the auth-refresh path to trigger the bypass.
    const { API_ENDPOINTS } = require('../constants/api');
    const errorHandler = stub.responseError[0];
    await expect(
      errorHandler({
        config: { url: API_ENDPOINTS.AUTH_REFRESH, headers: {} },
        response: { status: 401 },
      })
    ).rejects.toBeDefined();

    expect(lastAxiosPostMock).not.toHaveBeenCalled();
  });

  test('does not attempt refresh when no refresh token exists', async () => {
    const stub = stubAxiosInstance();
    importHttpClient(stub.instance);

    const errorHandler = stub.responseError[0];
    await expect(
      errorHandler({
        config: { url: '/anything', headers: {} },
        response: { status: 401 },
      })
    ).rejects.toBeDefined();

    expect(lastAxiosPostMock).not.toHaveBeenCalled();
  });
});
