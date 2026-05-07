import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

/**
 * Model Service
 * Handles all model-related API calls with proper error handling
 */

class ModelService {
  async getAllModels() {
    try {
      const response = await httpClient.get(`${API_ENDPOINTS.MODEL_LIST}/all/`);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to fetch models');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to fetch models'
      };
    }
  }

  async getModelById(modelId) {
    try {
      if (!modelId) {
        throw new Error('Model ID is required');
      }

      const response = await httpClient.get(API_ENDPOINTS.MODEL_DETAIL(modelId));
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to fetch model');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to fetch model'
      };
    }
  }

  async deleteModel(modelId) {
    try {
      if (!modelId) {
        throw new Error('Model ID is required');
      }

      const response = await httpClient.delete(API_ENDPOINTS.MODEL_DELETE(modelId));
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to delete model');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to delete model'
      };
    }
  }

  async createModel(modelData) {
    try {
      if (!modelData) {
        throw new Error('Model data is required');
      }

      const response = await httpClient.post(API_ENDPOINTS.MODEL_CREATE, modelData);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to create model');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to create model'
      };
    }
  }

  async updateModel(modelId, modelData) {
    try {
      if (!modelId) {
        throw new Error('Model ID is required');
      }
      if (!modelData) {
        throw new Error('Model data is required');
      }

      const response = await httpClient.put(API_ENDPOINTS.MODEL_UPDATE(modelId), modelData);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to update model');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to update model'
      };
    }
  }

  async getModelParameters() {
    try {
      const response = await httpClient.get(`${API_ENDPOINTS.MODEL_LIST}/parameters/`);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to fetch model parameters');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to fetch model parameters'
      };
    }
  }

  async getParameterOptions() {
    try {
      const response = await httpClient.get(`${API_ENDPOINTS.MODEL_LIST}/params/options/`);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to fetch parameter options');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to fetch parameter options'
      };
    }
  }

  async getParameterDefaultValues() {
    try {
      const response = await httpClient.get(`${API_ENDPOINTS.MODEL_LIST}/parameters/default-values/`);

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to fetch parameter default values');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to fetch parameter default values'
      };
    }
  }

  async getModelTypes() {
    try {
      const response = await httpClient.get(`${API_ENDPOINTS.MODEL_LIST}/types/`);

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to fetch model types');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to fetch model types'
      };
    }
  }
}

const modelServiceInstance = new ModelService();
export default modelServiceInstance;