import { useState, useCallback } from 'react';

/**
 * Custom hook for error handling
 * Provides consistent error management across components
 */

const useErrorHandler = () => {
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleError = useCallback((error) => {
    console.error('Error occurred:', error);
    
    if (typeof error === 'string') {
      setError(error);
    } else if (error?.message) {
      setError(error.message);
    } else {
      setError('An unexpected error occurred');
    }
    
    setIsLoading(false);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const executeAsync = useCallback(async (asyncFunction, options = {}) => {
    const { 
      onSuccess = null, 
      onError = null,
      showLoading = true,
      clearErrorOnStart = true
    } = options;

    try {
      if (clearErrorOnStart) {
        clearError();
      }
      
      if (showLoading) {
        setIsLoading(true);
      }

      const result = await asyncFunction();

      if (result && result.success === false) {
        throw new Error(result.error || 'Operation failed');
      }

      if (onSuccess) {
        onSuccess(result);
      }

      return result;
    } catch (err) {
      handleError(err);
      
      if (onError) {
        onError(err);
      }
      
      throw err;
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  }, [handleError, clearError]);

  return {
    error,
    isLoading,
    clearError,
    handleError,
    executeAsync
  };
};

export default useErrorHandler;