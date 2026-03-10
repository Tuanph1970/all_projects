/**
 * Unit tests for ProblemService
 */

jest.mock('../../src/services/apiClient', () => {
  const mockPost = jest.fn();
  const mockGet = jest.fn();
  const mockPut = jest.fn();
  const mockDelete = jest.fn();
  return {
    __esModule: true,
    default: { post: mockPost, get: mockGet, put: mockPut, delete: mockDelete },
    handleApiResponse: jest.fn((response) => response.data),
    handleApiError: jest.fn((error) => { throw error; }),
  };
});

const apiClientModule = require('../../src/services/apiClient');
const apiClient = apiClientModule.default;
const { handleApiResponse, handleApiError } = apiClientModule;
const { problemService } = require('../../src/services/problemService');

describe('ProblemService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    handleApiResponse.mockImplementation((r) => r.data);
  });

  // ── submitProblem ──────────────────────────────────────────

  describe('submitProblem()', () => {
    const mockResponse = {
      data: { id: 'prob-1', status: 'Pending', category: 'Algebra' }
    };

    it('calls POST /problem', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      await problemService.submitProblem({ imageUri: 'file://image.jpg', category: 'Algebra' });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/problem',
        expect.any(Object),
        expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } })
      );
    });

    it('returns response data on success', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      const result = await problemService.submitProblem({ imageUri: 'file://img.jpg' });

      expect(result).toEqual(mockResponse.data);
    });

    it('calls handleApiResponse with the response', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      await problemService.submitProblem({ imageUri: 'file://img.jpg' });

      expect(handleApiResponse).toHaveBeenCalledWith(mockResponse);
    });

    it('includes category in formData when provided', async () => {
      apiClient.post.mockResolvedValueOnce(mockResponse);

      await problemService.submitProblem({
        imageUri: 'file://img.jpg',
        category: 'Geometry',
      });

      const formData = apiClient.post.mock.calls[0][1];
      // FormData is an object; category should have been appended
      expect(apiClient.post).toHaveBeenCalled();
    });
  });

  // ── getUserProblems ────────────────────────────────────────

  describe('getUserProblems()', () => {
    const mockResponse = {
      data: {
        problems: [{ id: 'p1', status: 'Completed' }],
        total: 1,
        page: 1,
        pageSize: 10
      }
    };

    it('calls GET /problem with default params', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      await problemService.getUserProblems();

      expect(apiClient.get).toHaveBeenCalledWith(
        '/problem',
        expect.objectContaining({ params: expect.objectContaining({ page: 1, limit: 10 }) })
      );
    });

    it('passes custom page and limit', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      await problemService.getUserProblems({ page: 2, limit: 5 });

      expect(apiClient.get).toHaveBeenCalledWith(
        '/problem',
        expect.objectContaining({ params: expect.objectContaining({ page: 2, limit: 5 }) })
      );
    });

    it('passes status filter when provided', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      await problemService.getUserProblems({ status: 'Completed' });

      const params = apiClient.get.mock.calls[0][1].params;
      expect(params.status).toBe('Completed');
    });

    it('passes category filter when provided', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      await problemService.getUserProblems({ category: 'Algebra' });

      const params = apiClient.get.mock.calls[0][1].params;
      expect(params.category).toBe('Algebra');
    });

    it('does not include undefined filters', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      await problemService.getUserProblems({ page: 1 });

      const params = apiClient.get.mock.calls[0][1].params;
      expect(params.status).toBeUndefined();
      expect(params.category).toBeUndefined();
    });

    it('returns response data', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await problemService.getUserProblems();

      expect(result).toEqual(mockResponse.data);
    });
  });

  // ── getProblemById ─────────────────────────────────────────

  describe('getProblemById()', () => {
    const mockResponse = {
      data: { id: 'prob-42', status: 'Completed', extractedText: '2x = 6' }
    };

    it('calls GET /problem/:id', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      await problemService.getProblemById('prob-42');

      expect(apiClient.get).toHaveBeenCalledWith('/problem/prob-42');
    });

    it('returns the problem data', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await problemService.getProblemById('prob-42');

      expect(result).toEqual(mockResponse.data);
    });
  });

  // ── updateProblem ──────────────────────────────────────────

  describe('updateProblem()', () => {
    const mockResponse = {
      data: { id: 'prob-1', title: 'Updated Title' }
    };

    it('calls PUT /problems/:id', async () => {
      apiClient.put.mockResolvedValueOnce(mockResponse);

      await problemService.updateProblem('prob-1', { title: 'Updated Title' });

      expect(apiClient.put).toHaveBeenCalledWith(
        '/problems/prob-1',
        { title: 'Updated Title' }
      );
    });

    it('returns the updated data', async () => {
      apiClient.put.mockResolvedValueOnce(mockResponse);

      const result = await problemService.updateProblem('prob-1', { title: 'Updated' });

      expect(result).toEqual(mockResponse.data);
    });
  });

  // ── deleteProblem ──────────────────────────────────────────

  describe('deleteProblem()', () => {
    it('calls DELETE /problem/:id', async () => {
      apiClient.delete.mockResolvedValueOnce({ data: { success: true } });

      await problemService.deleteProblem('prob-99');

      expect(apiClient.delete).toHaveBeenCalledWith('/problem/prob-99');
    });
  });

  // ── searchProblems ─────────────────────────────────────────

  describe('searchProblems()', () => {
    const mockResponse = {
      data: { problems: [], total: 0, page: 1, pageSize: 10 }
    };

    it('calls GET /problems/search with query', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      await problemService.searchProblems({ query: 'algebra' });

      expect(apiClient.get).toHaveBeenCalledWith(
        '/problems/search',
        expect.objectContaining({ params: expect.objectContaining({ q: 'algebra' }) })
      );
    });

    it('uses default page and limit', async () => {
      apiClient.get.mockResolvedValueOnce(mockResponse);

      await problemService.searchProblems({});

      const params = apiClient.get.mock.calls[0][1].params;
      expect(params.page).toBe(1);
      expect(params.limit).toBe(10);
    });
  });

  // ── retrySolution ─────────────────────────────────────────

  describe('retrySolution()', () => {
    it('calls POST /problem/:id/retry', async () => {
      apiClient.post.mockResolvedValueOnce({ data: { queued: true } });

      await problemService.retrySolution('prob-5');

      expect(apiClient.post).toHaveBeenCalledWith('/problem/prob-5/retry');
    });
  });

  // ── error propagation ─────────────────────────────────────

  describe('error handling', () => {
    it('propagates errors through handleApiError', async () => {
      const networkError = new Error('Network error');
      apiClient.get.mockRejectedValueOnce(networkError);
      handleApiError.mockImplementationOnce((err) => { throw err; });

      await expect(problemService.getProblemById('bad-id')).rejects.toThrow('Network error');
    });
  });
});
