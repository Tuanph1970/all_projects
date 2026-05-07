import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

/**
 * File Service
 * Handles all file-related API calls with proper error handling
 */

class FileService {
  async getFileList() {
    try {
      const response = await httpClient.get(API_ENDPOINTS.FILE_LIST);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to fetch file list');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to fetch file list'
      };
    }
  }

  async uploadFile(file) {
    try {
      if (!file) {
        throw new Error('File is required');
      }

      const formData = new FormData();
      formData.append('file', file);

      const response = await httpClient.post(API_ENDPOINTS.FILE_UPLOAD, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to upload file');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to upload file'
      };
    }
  }

  async deleteFile(filename) {
    try {
      if (!filename) {
        throw new Error('Filename is required');
      }

      const response = await httpClient.delete(`${API_ENDPOINTS.FILE_DELETE}/${filename}`);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to delete file');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to delete file'
      };
    }
  }

  async processFile(filename) {
    try {
      if (!filename) {
        throw new Error('Filename is required');
      }

      const response = await httpClient.post(`${API_ENDPOINTS.FILE_PROCESS}/${filename}`);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to process file');
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to process file'
      };
    }
  }
}

const fileServiceInstance = new FileService();
export default fileServiceInstance;