import React from 'react';

const ConfirmDialog = ({
  show,
  isOpen,
  title = 'Xác nhận hành động',
  message = 'Bạn có chắc chắn muốn tiếp tục?',
  confirmText = 'Xác nhận',
  cancelText = 'Hủy',
  onConfirm,
  onCancel,
  variant = 'danger',
  isLoading = false
}) => {
  // Accept both 'show' and 'isOpen' props for compatibility
  const isVisible = show || isOpen;
  if (!isVisible) return null;

  return (
    <div
      className="modal-overlay"
      onClick={onCancel}
      style={{
        display: 'flex',
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 999999,
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          display: 'block',
          backgroundColor: 'white',
          padding: '1.5rem',
          borderRadius: '0.5rem',
          minWidth: '400px',
          maxWidth: '500px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
          position: 'relative'
        }}
      >
        <div className="modal-header">
          <h2 className="modal-title">{title}</h2>
          <button 
            type="button" 
            className="modal-close"
            aria-label="Close"
            onClick={onCancel}
            disabled={isLoading}
          >
            ×
          </button>
        </div>
        <div className="modal-body">
          <p>{message}</p>
        </div>
        <div className="modal-footer">
          <button 
            type="button" 
            className="btn btn-secondary" 
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelText}
          </button>
          <button 
            type="button" 
            className={`btn btn-${variant === 'danger' ? 'danger' : 'primary'}`}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="spinner" role="status" aria-hidden="true"></span>
                Đang xử lý...
              </>
            ) : (
              confirmText
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;