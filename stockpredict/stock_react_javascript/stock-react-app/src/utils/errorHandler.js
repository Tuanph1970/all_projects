/**
 * Global Error Handler Utility
 * Provides centralized error handling and logging
 */

export const logError = (error, context = '') => {
  const errorInfo = {
    message: error.message || 'Unknown error',
    stack: error.stack,
    context,
    timestamp: new Date().toISOString(),
    url: window.location.href,
    userAgent: navigator.userAgent
  };

  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.error('Error logged:', errorInfo);
  }

  // In production, you might want to send this to an external logging service
  // Example: sendToLoggingService(errorInfo);
};

export const formatErrorMessage = (error) => {
  if (typeof error === 'string') {
    return error;
  }
  
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  
  if (error.message) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
};

export const isNetworkError = (error) => {
  return error.code === 'NETWORK_ERROR' || 
         error.message?.includes('Network Error') ||
         error.message?.includes('fetch');
};

export const handleApiError = (error, context = '') => {
  logError(error, context);
  
  if (isNetworkError(error)) {
    return 'Network error. Please check your connection and try again.';
  }
  
  if (error.response?.status === 401) {
    return 'You are not authorized to perform this action.';
  }
  
  if (error.response?.status === 403) {
    return 'Access denied. You do not have permission to access this resource.';
  }
  
  if (error.response?.status === 404) {
    return 'The requested resource was not found.';
  }
  
  if (error.response?.status >= 500) {
    return 'Server error. Please try again later.';
  }
  
  return formatErrorMessage(error);
};