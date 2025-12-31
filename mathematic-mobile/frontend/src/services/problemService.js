import apiClient, { handleApiResponse, handleApiError } from './apiClient';

class ProblemService {
  // Submit a new problem
  async submitProblem({ imageUri, category, description }) {
    try {
      const formData = new FormData();
      
      // Add image file
      if (imageUri) {
        const filename = imageUri.split('/').pop();
        const match = /\\.([\\w\\d_-]+)$/i.exec(filename);
        const type = match ? `image/${match[1]}` : 'image/jpeg';
        
        formData.append('ImageFile', {
          uri: imageUri,
          name: filename,
          type,
        });
      }

      // Add other data - field names must match backend (Pascal case)
      if (category) {
        formData.append('Category', category);
      }
      if (description) {
        formData.append('Description', description);
      }
      
      const response = await apiClient.post('/problem', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 60000, // 60 seconds for image upload + ML processing
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get user's problems
  async getUserProblems({ page = 1, limit = 10, category, status } = {}) {
    try {
      const params = {
        page,
        limit,
      };
      
      if (category) {
        params.category = category;
      }
      if (status) {
        params.status = status;
      }
      
      const response = await apiClient.get('/problem', { params });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get problem by ID
  async getProblemById(problemId) {
    try {
      const response = await apiClient.get(`/problem/${problemId}`);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Update problem
  async updateProblem(problemId, updates) {
    try {
      const response = await apiClient.put(`/problems/${problemId}`, updates);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Delete problem
  async deleteProblem(problemId) {
    try {
      const response = await apiClient.delete(`/problem/${problemId}`);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Search problems
  async searchProblems({ query, category, dateFrom, dateTo, page = 1, limit = 10 } = {}) {
    try {
      const params = {
        page,
        limit,
      };
      
      if (query) {
        params.q = query;
      }
      if (category) {
        params.category = category;
      }
      if (dateFrom) {
        params.dateFrom = dateFrom;
      }
      if (dateTo) {
        params.dateTo = dateTo;
      }
      
      const response = await apiClient.get('/problems/search', { params });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get problem categories
  async getCategories() {
    try {
      const response = await apiClient.get('/problems/categories');
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get problem statistics
  async getProblemStats() {
    try {
      const response = await apiClient.get('/problems/stats');
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Report problem
  async reportProblem(problemId, reason, description) {
    try {
      const response = await apiClient.post(`/problems/${problemId}/report`, {
        reason,
        description,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Retry solving problem
  async retrySolution(problemId) {
    try {
      const response = await apiClient.post(`/problem/${problemId}/retry`);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get problem solving status
  async getProblemStatus(problemId) {
    try {
      const response = await apiClient.get(`/problems/${problemId}/status`);
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }
}

export const problemService = new ProblemService();