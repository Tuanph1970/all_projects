import React from 'react';

const ErrorMessage = ({ 
  message, 
  variant = 'danger', 
  className = '',
  onRetry = null,
  dismissible = false,
  onDismiss = null 
}) => {
  if (!message) return null;

  return (
    <div className={`alert alert-${variant} ${dismissible ? 'alert-dismissible' : ''} ${className}`} role="alert">
      <div className="d-flex align-items-center">
        <i className="fas fa-exclamation-triangle me-2"></i>
        <div className="flex-grow-1">
          {message}
        </div>
        <div className="d-flex gap-2 ms-2">
          {onRetry && (
            <button
              type="button"
              className="btn btn-sm btn-outline-danger"
              onClick={onRetry}
            >
              Thử lại
            </button>
          )}
          {dismissible && (
            <button 
              type="button" 
              className="btn-close" 
              aria-label="Close"
              onClick={onDismiss}
            ></button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ErrorMessage;