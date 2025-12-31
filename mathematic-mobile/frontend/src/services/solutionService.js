import apiClient, { handleApiResponse, handleApiError } from './apiClient';

class SolutionService {
  // Get solution by problem ID
  async getSolutionByProblemId(problemId) {
    try {
      const response = await apiClient.get(`/solutions/problem/${problemId}`);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get solution by ID
  async getSolutionById(solutionId) {
    try {
      const response = await apiClient.get(`/solutions/${solutionId}`);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Rate solution
  async rateSolution(solutionId, rating, feedback) {
    try {
      const response = await apiClient.post(`/solutions/${solutionId}/rate`, {
        rating,
        feedback,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Request hint for a specific step
  async requestHint(problemId, currentStep) {
    try {
      const response = await apiClient.post('/solutions/hint', {
        problemId,
        currentStep,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Request explanation for a step
  async requestExplanation(solutionId, stepIndex) {
    try {
      const response = await apiClient.post(`/solutions/${solutionId}/explain`, {
        stepIndex,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get similar solutions
  async getSimilarSolutions(solutionId, limit = 5) {
    try {
      const response = await apiClient.get(`/solutions/${solutionId}/similar`, {
        params: { limit },
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Report solution issue
  async reportSolution(solutionId, issueType, description) {
    try {
      const response = await apiClient.post(`/solutions/${solutionId}/report`, {
        issueType,
        description,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Export solution
  async exportSolution(solutionId, format = 'pdf') {
    try {
      const response = await apiClient.get(`/solutions/${solutionId}/export`, {
        params: { format },
        responseType: 'blob',
      });
      
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // Share solution
  async shareSolution(solutionId, shareType = 'link') {
    try {
      const response = await apiClient.post(`/solutions/${solutionId}/share`, {
        shareType,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get solution statistics
  async getSolutionStats(solutionId) {
    try {
      const response = await apiClient.get(`/solutions/${solutionId}/stats`);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get user's solution history
  async getUserSolutions({ page = 1, limit = 10, category, dateFrom, dateTo } = {}) {
    try {
      const params = {
        page,
        limit,
      };
      
      if (category) {
        params.category = category;
      }
      if (dateFrom) {
        params.dateFrom = dateFrom;
      }
      if (dateTo) {
        params.dateTo = dateTo;
      }
      
      const response = await apiClient.get('/solutions/history', { params });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Bookmark solution
  async bookmarkSolution(solutionId) {
    try {
      const response = await apiClient.post(`/solutions/${solutionId}/bookmark`);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Remove bookmark from solution
  async removeBookmark(solutionId) {
    try {
      const response = await apiClient.delete(`/solutions/${solutionId}/bookmark`);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get bookmarked solutions
  async getBookmarkedSolutions({ page = 1, limit = 10 } = {}) {
    try {
      const response = await apiClient.get('/solutions/bookmarks', {
        params: { page, limit },
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }
}

export const solutionService = new SolutionService();