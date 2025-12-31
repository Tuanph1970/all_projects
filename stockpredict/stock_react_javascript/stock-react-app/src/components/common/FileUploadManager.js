import React, { useState, useEffect } from "react";
import { Button, ButtonGroup } from "react-bootstrap";
import fileService from "../../services/fileService";
import { useErrorHandler } from "../../hooks";
import { DataTable, LoadingSpinner, ErrorMessage, ConfirmDialog } from "../ui";
import FileUploader from "../WebControl/FileUploader";

const FileUploadManager = () => {
  const [fileListData, setFileListData] = useState([]);
  const [deleteConfirm, setDeleteConfirm] = useState({ show: false, fileId: null, fileName: '' });
  const [processingFile, setProcessingFile] = useState(null);
  const { error, isLoading, clearError, executeAsync } = useErrorHandler();

  const getFileUploadList = async () => {
    try {
      await executeAsync(async () => {
        const result = await fileService.getFileList();
        if (result.success) {
          setFileListData(result.data || []);
        }
        return result;
      });
    } catch (err) {
      console.error('Failed to fetch file list:', err);
    }
  };

  const handleDeleteFile = async (fileId) => {
    try {
      await executeAsync(async () => {
        const result = await fileService.deleteFile(fileId);
        if (result.success) {
          await getFileUploadList();
          setDeleteConfirm({ show: false, fileId: null, fileName: '' });
        }
        return result;
      });
    } catch (err) {
      console.error('Failed to delete file:', err);
    }
  };

  const handleProcessFile = async (fileId) => {
    try {
      setProcessingFile(fileId);
      await executeAsync(async () => {
        const result = await fileService.processFile(fileId);
        if (result.success) {
          await getFileUploadList();
        }
        return result;
      }, { showLoading: false });
    } catch (err) {
      console.error('Failed to process file:', err);
    } finally {
      setProcessingFile(null);
    }
  };

  const handleUploadComplete = async () => {
    await getFileUploadList();
  };

  const showDeleteConfirm = (fileId, fileName) => {
    setDeleteConfirm({ show: true, fileId, fileName });
  };

  const hideDeleteConfirm = () => {
    setDeleteConfirm({ show: false, fileId: null, fileName: '' });
  };

  const getFileStatusText = (status) => {
    switch (status) {
      case 0: return 'Pending';
      case 1: return 'Processed';
      case 2: return 'Error';
      default: return 'Unknown';
    }
  };

  const getFileStatusBadge = (status) => {
    const statusMap = {
      0: 'warning',
      1: 'success',
      2: 'danger'
    };
    return statusMap[status] || 'secondary';
  };

  const columns = [
    {
      header: 'File Name',
      key: 'file_name',
      render: (row) => (
        <div>
          <strong>{row.file_name}</strong>
          <br />
          <small className="text-muted">ID: {row.id}</small>
        </div>
      )
    },
    {
      header: 'Status',
      key: 'file_status',
      render: (row) => (
        <span className={`badge bg-${getFileStatusBadge(row.file_status)}`}>
          {getFileStatusText(row.file_status)}
        </span>
      )
    },
    {
      header: 'Owner ID',
      key: 'owner_id'
    }
  ];

  const renderActions = (row) => (
    <ButtonGroup>
      {row.file_status === 0 && (
        <Button 
          variant="primary" 
          size="sm"
          onClick={() => handleProcessFile(row.id)}
          disabled={processingFile === row.id}
        >
          {processingFile === row.id ? (
            <>
              <span className="spinner-border spinner-border-sm me-1" />
              Processing...
            </>
          ) : (
            'Process'
          )}
        </Button>
      )}
      <Button 
        variant="outline-danger" 
        size="sm"
        onClick={() => showDeleteConfirm(row.id, row.file_name)}
      >
        Delete
      </Button>
    </ButtonGroup>
  );

  useEffect(() => {
    getFileUploadList();
  }, []);

  return (
    <div className="file-upload-manager">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5>File Management</h5>
        <FileUploader uploadHandler={handleUploadComplete} />
      </div>

      {error && (
        <ErrorMessage 
          message={error} 
          onRetry={getFileUploadList}
          dismissible
          onDismiss={clearError}
          className="mb-3"
        />
      )}

      <DataTable
        data={fileListData}
        columns={columns}
        loading={isLoading}
        error={null}
        onRetry={getFileUploadList}
        emptyMessage="No files uploaded yet"
        actions={renderActions}
        className="mb-3"
      />

      <ConfirmDialog
        show={deleteConfirm.show}
        title="Delete File"
        message={`Are you sure you want to delete "${deleteConfirm.fileName}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onConfirm={() => handleDeleteFile(deleteConfirm.fileId)}
        onCancel={hideDeleteConfirm}
        isLoading={isLoading}
      />
    </div>
  );
};

export default FileUploadManager;