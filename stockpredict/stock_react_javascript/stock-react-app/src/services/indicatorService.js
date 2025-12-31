import { API_ENDPOINTS } from '../constants/api';

/**
 * Indicator Service
 * Routes to Prediction Service via /api/v2/predict/indicators
 */
class IndicatorService {
  /**
   * Get all technical indicators grouped by category
   */
  async getAllIndicators() {
    const response = await fetch(API_ENDPOINTS.INDICATORS_LIST);
    if (!response.ok) {
      throw new Error('Failed to fetch indicators');
    }
    return response.json();
  }

  /**
   * Get indicators by type (trend, momentum, volatility, volume)
   */
  async getIndicatorsByType(type) {
    const response = await fetch(API_ENDPOINTS.INDICATORS_BY_TYPE(type));
    if (!response.ok) {
      throw new Error(`Failed to fetch ${type} indicators`);
    }
    return response.json();
  }

  /**
   * Get specific indicator details
   */
  async getIndicatorById(indicatorId) {
    const response = await fetch(API_ENDPOINTS.INDICATOR_DETAIL(indicatorId));
    if (!response.ok) {
      throw new Error('Failed to fetch indicator details');
    }
    return response.json();
  }

  /**
   * Calculate indicator values
   */
  async calculateIndicator(data) {
    const response = await fetch(API_ENDPOINTS.INDICATOR_CALCULATE, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to calculate indicator');
    }
    return response.json();
  }

  /**
   * Get indicators configured for a solution
   */
  async getSolutionIndicators(solutionId) {
    const response = await fetch(API_ENDPOINTS.SOLUTION_INDICATORS(solutionId));
    if (!response.ok) {
      throw new Error('Failed to fetch solution indicators');
    }
    return response.json();
  }

  /**
   * Add an indicator to a solution
   */
  async addSolutionIndicator(solutionId, data) {
    const response = await fetch(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/add`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to add indicator to solution');
    }
    return response.json();
  }

  /**
   * Update indicator parameters for a solution
   */
  async updateSolutionIndicator(solutionId, indicatorId, data) {
    const response = await fetch(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/${indicatorId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to update solution indicator');
    }
    return response.ok;
  }

  /**
   * Remove an indicator from a solution
   */
  async removeSolutionIndicator(solutionId, indicatorId) {
    const response = await fetch(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/${indicatorId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to remove solution indicator');
    }
    return response.ok;
  }

  /**
   * Set all four indicators for a solution at once
   */
  async setSolutionIndicators(solutionId, data) {
    const response = await fetch(API_ENDPOINTS.SOLUTION_INDICATORS_SET(solutionId), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to set solution indicators');
    }
    return response.json();
  }

  /**
   * Calculate all indicators for a solution
   */
  async calculateSolutionIndicators(solutionId, data) {
    const response = await fetch(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/calculate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to calculate solution indicators');
    }
    return response.json();
  }

  /**
   * Validate that a solution has all required indicators
   */
  async validateSolutionIndicators(solutionId) {
    const response = await fetch(`${API_ENDPOINTS.SOLUTION_INDICATORS(solutionId)}/validate`);
    if (!response.ok) {
      throw new Error('Failed to validate solution indicators');
    }
    return response.json();
  }

  /**
   * Create a new technical indicator
   */
  async createIndicator(data) {
    const response = await fetch(API_ENDPOINTS.INDICATOR_CREATE, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to create indicator');
    }
    return response.json();
  }

  /**
   * Update an existing technical indicator
   */
  async updateIndicator(indicatorId, data) {
    const response = await fetch(API_ENDPOINTS.INDICATOR_UPDATE(indicatorId), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to update indicator');
    }
    return response.json();
  }

  /**
   * Delete a technical indicator
   */
  async deleteIndicator(indicatorId) {
    const response = await fetch(API_ENDPOINTS.INDICATOR_DELETE(indicatorId), {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete indicator');
    }
    return response.ok;
  }
}

export default new IndicatorService();
