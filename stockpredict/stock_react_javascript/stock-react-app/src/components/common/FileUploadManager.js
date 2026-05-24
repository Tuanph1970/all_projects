import React, { useState, useEffect } from "react";
import { useTranslation } from 'react-i18next';
import { Button, ButtonGroup } from "react-bootstrap";
import fileService from "../../services/fileService";
import { useErrorHandler } from "../../hooks";
import { DataTable, ErrorMessage, ConfirmDialog } from "../ui";
import FileUploader from "../WebControl/FileUploader";

const FileUploadManager = () => {
  const { t } = useTranslation();
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
      case 0: return t('file_manager.status_pending');
      case 1: return t('file_manager.status_processed');
      case 2: return t('file_manager.status_error');
      default: return t('file_manager.status_unknown');
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
      header: t('file_manager.col_file_name'),
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
      header: t('file_manager.col_status'),
      key: 'file_status',
      render: (row) => (
        <span className={`badge bg-${getFileStatusBadge(row.file_status)}`}>
          {getFileStatusText(row.file_status)}
        </span>
      )
    },
    {
      header: t('file_manager.col_owner'),
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
              {t('file_manager.processing_btn')}
            </>
          ) : (
            t('file_manager.process_btn')
          )}
        </Button>
      )}
      <Button 
        variant="outline-danger" 
        size="sm"
        onClick={() => showDeleteConfirm(row.id, row.file_name)}
      >
        {t('file_manager.delete_btn')}
      </Button>
    </ButtonGroup>
  );

  useEffect(() => {
    getFileUploadList();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="file-upload-manager">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5>{t('file_manager.title')}</h5>
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
        emptyMessage={t('file_manager.empty_msg')}
        actions={renderActions}
        className="mb-3"
      />

      <ConfirmDialog
        show={deleteConfirm.show}
        title={t('file_manager.delete_title')}
        message={t('file_manager.delete_confirm', { name: deleteConfirm.fileName })}
        confirmText={t('file_manager.confirm_btn')}
        cancelText={t('file_manager.cancel_btn')}
        variant="danger"
        onConfirm={() => handleDeleteFile(deleteConfirm.fileId)}
        onCancel={hideDeleteConfirm}
        isLoading={isLoading}
      />
    </div>
  );
};

export default FileUploadManager;