import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

/**
 * Indicator Service
 * Routes to Prediction Service via /api/v2/predict/indicators
 * Uses httpClient for automatic auth token handling
 */
class IndicatorService {
  /**
   * Get all technical indicators grouped by category
   */
  async getAllIndicators() {
    const response = await httpClient.get(API_ENDPOINTS.INDICATORS_LIST);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to fetch indicators');
    }
    return response.data;
  }

  /**
   * Get indicators by type (trend, momentum, volatility, volume)
   */
  async getIndicatorsByType(type) {
    const response = await httpClient.get(API_ENDPOINTS.INDICATORS_BY_TYPE(type));
    if (!response.success) {
      throw new Error(response.error?.message || `Failed to fetch ${type} indicators`);
    }
    return response.data;
  }

  /**
   * Get specific indicator details
   */
  async getIndicatorById(indicatorId) {
    const response = await httpClient.get(API_ENDPOINTS.INDICATOR_DETAIL(indicatorId));
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to fetch indicator details');
    }
    return response.data;
  }

  /**
   * Calculate indicator values
   */
  async calculateIndicator(data) {
    const response = await httpClient.post(API_ENDPOINTS.INDICATOR_CALCULATE, data);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to calculate indicator');
    }
    return response.data;
  }

  /**
   * Get indicators configured for a solution
   */
  async getSolutionIndicators(solutionId) {
    const response = await httpClient.get(API_ENDPOINTS.SOLUTION_INDICATORS(solutionId));
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to fetch solution indicators');
    }
    return response.data;
  }

  /**
   * Add an indicator to a solution
   */
  async addSolutionIndicator(solutionId, data) {
    const response = await httpClient.post(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/add`, data);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to add indicator to solution');
    }
    return response.data;
  }

  /**
   * Update indicator parameters for a solution
   */
  async updateSolutionIndicator(solutionId, indicatorId, data) {
    const response = await httpClient.put(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/${indicatorId}`, data);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to update solution indicator');
    }
    return response.data;
  }

  /**
   * Remove an indicator from a solution
   */
  async removeSolutionIndicator(solutionId, indicatorId) {
    const response = await httpClient.delete(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/${indicatorId}`);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to remove solution indicator');
    }
    return response.data;
  }

  /**
   * Set all four indicators for a solution at once
   */
  async setSolutionIndicators(solutionId, data) {
    const response = await httpClient.post(API_ENDPOINTS.SOLUTION_INDICATORS_SET(solutionId), data);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to set solution indicators');
    }
    return response.data;
  }

  /**
   * Calculate all indicators for a solution
   */
  async calculateSolutionIndicators(solutionId, data) {
    const response = await httpClient.post(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/calculate`, data);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to calculate solution indicators');
    }
    return response.data;
  }

  /**
   * Validate that a solution has all required indicators
   */
  async validateSolutionIndicators(solutionId) {
    const response = await httpClient.get(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/validate`);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to validate solution indicators');
    }
    return response.data;
  }

  /**
   * Create a new technical indicator
   */
  async createIndicator(data) {
    const response = await httpClient.post(API_ENDPOINTS.INDICATOR_CREATE, data);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to create indicator');
    }
    return response.data;
  }

  /**
   * Update an existing technical indicator
   */
  async updateIndicator(indicatorId, data) {
    const response = await httpClient.put(API_ENDPOINTS.INDICATOR_UPDATE(indicatorId), data);
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to update indicator');
    }
    return response.data;
  }

  /**
   * Delete a technical indicator
   */
  async deleteIndicator(indicatorId) {
    const response = await httpClient.delete(API_ENDPOINTS.INDICATOR_DELETE(indicatorId));
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to delete indicator');
    }
    return response.data;
  }
}

const indicatorServiceInstance = new IndicatorService();
export default indicatorServiceInstance;
