import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

/**
 * Solution Service
 * Handles all solution-related API calls with proper error handling
 */

class SolutionService {
  async getAllSolutions() {
    try {
      const response = await httpClient.get(`${API_ENDPOINTS.SOLUTION_LIST}/all/`);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to fetch solutions');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to fetch solutions'
      };
    }
  }

  async getSolutionById(solutionId) {
    try {
      if (!solutionId) {
        throw new Error('Solution ID is required');
      }

      const response = await httpClient.get(API_ENDPOINTS.SOLUTION_DETAIL(solutionId));
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to fetch solution');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to fetch solution'
      };
    }
  }

  async deleteSolution(solutionId) {
    try {
      if (!solutionId) {
        throw new Error('Solution ID is required');
      }

      const response = await httpClient.delete(API_ENDPOINTS.SOLUTION_DELETE(solutionId));
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to delete solution');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to delete solution'
      };
    }
  }

  async createSolution(solutionData) {
    try {
      if (!solutionData) {
        throw new Error('Solution data is required');
      }

      const response = await httpClient.post(API_ENDPOINTS.SOLUTION_CREATE, solutionData);

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to create solution');
      }

      // If backend doesn't return the created solution, return the sent data
      // The backend should ideally return the created solution with its ID
      return {
        success: true,
        data: response.data || solutionData
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to create solution'
      };
    }
  }

  async updateSolution(solutionId, solutionData) {
    try {
      if (!solutionId) {
        throw new Error('Solution ID is required');
      }
      if (!solutionData) {
        throw new Error('Solution data is required');
      }

      // Ensure the ID is in the data for backend processing
      const dataWithId = {
        ...solutionData,
        id: solutionId
      };

      const response = await httpClient.put(API_ENDPOINTS.SOLUTION_UPDATE(solutionId), dataWithId);

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to update solution');
      }

      return {
        success: true,
        data: response.data || dataWithId // Return the updated data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to update solution'
      };
    }
  }
}

const solutionServiceInstance = new SolutionService();
export default solutionServiceInstance;