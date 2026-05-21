import React, { useEffect, useState } from "react";
import { Button } from "react-bootstrap";
import DataTable from 'react-data-table-component'
import { useTranslation } from "react-i18next";
import solutionService from "../../../services/solutionService";
import SolutionModal from "./SolutionModal";
import "../../../styles/solution-list.css";

const SolutionList = () => {
  const { t, i18n } = useTranslation();
  // navigate was destructured here but never called — dropped during the
  // useRouter → react-router migration. Add useNavigate back if needed.
  const [solutionList, setSolutionList] = useState([]);
  const [filteredSolutions, setFilteredSolutions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'not_trained', 'trained', 'predicted'

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [selectedSolution, setSelectedSolution] = useState(null);

  useEffect(() => {
    loadSolutions();
  }, []);

  useEffect(() => {
    // Client-side filtering by search term and status
    let filtered = solutionList;

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter(solution => solution.train_status === statusFilter);
    }

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(solution =>
        solution.solution_name?.toLowerCase().includes(term) ||
        solution.ticker?.toLowerCase().includes(term) ||
        solution.model_type?.toLowerCase().includes(term) ||
        solution.model_sub_type?.toLowerCase().includes(term) ||
        solution.created_by?.toLowerCase().includes(term) ||
        solution.train_status?.toLowerCase().includes(term)
      );
    }

    setFilteredSolutions(filtered);
  }, [solutionList, searchTerm, statusFilter]);

  // Calculate status counts
  const statusCounts = {
    all: solutionList.length,
    not_trained: solutionList.filter(s => s.train_status === 'not_trained' || !s.train_status).length,
    trained: solutionList.filter(s => s.train_status === 'trained').length,
    predicted: solutionList.filter(s => s.train_status === 'predicted').length
  };

  const onAddNew = () => {
    setSelectedSolution(null);
    setShowModal(true);
  }

  const loadSolutions = async () => {
    try {      
      setIsLoading(true);
      setError(null);
      
      const result = await solutionService.getAllSolutions();
      
      if (result.success) {
        setSolutionList(result.data);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(t('solutions.load_error'));
    } finally {
      setIsLoading(false);
    }
  }

  const editSolution = async (event) => {
    const id = parseInt(event.target.id);
    if (id > 0) {
      // Load solution details
      const result = await solutionService.getSolutionById(id);
      if (result.success) {
        setSelectedSolution(result.data);
        setShowModal(true);
      } else {
        setError(result.error);
      }
    }
  }

  const deleteSolution = async (event) => {  
    const id = parseInt(event.target.id);
    if (id > 0) {
      // Show confirmation dialog
      if (window.confirm(t('solutions.delete_confirm'))) {
        try {
          const result = await solutionService.deleteSolution(id);

          if (result.success) {
            // Refresh the list after successful deletion
            loadSolutions();
          } else {
            setError(result.error);
          }
        } catch (err) {
          setError(t('solutions.delete_error'));
        }
      }
    }
  }

  const handleModalClose = () => {
    setShowModal(false);
    setSelectedSolution(null);
  };

  const handleModalSave = (savedSolution) => {
    // Refresh the solutions list
    loadSolutions();
    // Close modal after a short delay to show success message
    setTimeout(() => {
      handleModalClose();
    }, 1500);
  };

  // Helper function to render train status badge
  const renderTrainStatusBadge = (status) => {
    const statusConfig = {
      'not_trained': {
        label: t('solutions.status_not_trained'),
        className: 'badge bg-secondary',
        icon: '○'
      },
      'trained': {
        label: t('solutions.status_trained'),
        className: 'badge bg-success',
        icon: '✓'
      },
      'predicted': {
        label: t('solutions.status_predicted'),
        className: 'badge bg-primary',
        icon: '★'
      }
    };

    const config = statusConfig[status] || statusConfig['not_trained'];

    return (
      <span className={config.className} style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}>
        {config.icon} {config.label}
      </span>
    );
  };

  // Use the active language for date formatting so dates match the rest
  // of the UI when the user switches to English.
  const dateLocale = i18n.language === 'en' ? 'en-GB' : 'vi-VN';

  const general_columns = [
        {
            name: 'ID',
            selector: row => row.id,
            omit: true,
        },
        {
          name: t('solutions.column_name'),
          selector: row => row.solution_name,
          sortable: true,
          grow: 2,
          style: {
            fontWeight: '500',
            color: '#1f2937',
          }
        },
        {
            name: t('solutions.column_ticker'),
            selector: row => row.ticker,
            sortable: true,
            width: '100px',
            style: {
              fontWeight: '600',
              color: '#2563eb',
            }
        },
        {
          name: t('solutions.column_status'),
          selector: row => row.train_status,
          sortable: true,
          width: '130px',
          cell: (row) => renderTrainStatusBadge(row.train_status)
        },
        {
          name: t('solutions.column_model_type'),
          selector: row => row.model_type,
          sortable: true,
          width: '120px',
        },
        {
          name: t('solutions.column_sub_type'),
          selector: row => row.model_sub_type,
          sortable: true,
          width: '130px',
        },
        {
            name: t('solutions.column_model_name'),
            selector: row => row.model_name,
            sortable: true,
            width: '130px',
        },
        {
            name: t('solutions.column_creator'),
            selector: row => row.created_by,
            sortable: true,
            width: '110px',
        },
        {
            name: t('solutions.column_created_date'),
            selector: row => row.created_date,
            sortable: true,
            width: '120px',
            format: row => {
              if (!row.created_date) return '-';
              return new Date(row.created_date).toLocaleDateString(dateLocale);
            }
        },
        {
            name: t('solutions.column_updated_date'),
            selector: row => row.updated_date,
            sortable: true,
            width: '120px',
            format: row => {
              if (!row.updated_date) return '-';
              return new Date(row.updated_date).toLocaleDateString(dateLocale);
            }
        },
        {
          name: t('solutions.column_actions'),
          width: "180px",
          center: true,
          cell: (row) => (
              <div className="action-buttons">
                 <Button
                   variant="outline-primary"
                   size="sm"
                   onClick={editSolution}
                   id={row.id}
                   className="action-btn-edit"
                 >
                   {t('solutions.edit')}
                 </Button>
                 <Button
                   variant="outline-danger"
                   size="sm"
                   onClick={deleteSolution}
                   id={row.id}
                   className="action-btn-delete"
                 >
                   {t('solutions.delete')}
                 </Button>
              </div>
          )
      },
    ];
  if (isLoading) {
    return (
      <div className="solution-loading">
        <span className="loading-spinner"></span>
        {t('solutions.loading')}
      </div>
    );
  }

  return (
    <div className="solution-list-container">
      <div className="solution-header">
        <div className="header-content">
          <h1>{t('solutions.title')}</h1>
          <p className="header-subtitle">{t('solutions.subtitle')}</p>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <strong>{t('solutions.error_label')}</strong> {error}
        </div>
      )}

      <div className="solution-controls">
        <div className="solution-filters">
          <input
            type="text"
            placeholder={`🔍 ${t('solutions.search_placeholder')}`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="filter-input"
          />
        </div>

        <div className="solution-actions">
          <Button variant="primary" onClick={onAddNew} className="btn btn-primary">
            {t('solutions.add_new')}
          </Button>
        </div>
      </div>

      <div className="solution-stats">
        <div
          className={`stat-card ${statusFilter === 'all' ? 'active' : ''}`}
          onClick={() => setStatusFilter('all')}
          style={{ cursor: 'pointer' }}
        >
          <span className="stat-label">{t('solutions.filter_all')}</span>
          <span className="stat-value">{statusCounts.all}</span>
        </div>
        <div
          className={`stat-card ${statusFilter === 'not_trained' ? 'active' : ''}`}
          onClick={() => setStatusFilter('not_trained')}
          style={{ cursor: 'pointer', borderLeft: '3px solid #6b7280' }}
        >
          <span className="stat-label">{t('solutions.filter_not_trained')}</span>
          <span className="stat-value">{statusCounts.not_trained}</span>
        </div>
        <div
          className={`stat-card ${statusFilter === 'trained' ? 'active' : ''}`}
          onClick={() => setStatusFilter('trained')}
          style={{ cursor: 'pointer', borderLeft: '3px solid #22c55e' }}
        >
          <span className="stat-label">{t('solutions.filter_trained')}</span>
          <span className="stat-value">{statusCounts.trained}</span>
        </div>
        <div
          className={`stat-card ${statusFilter === 'predicted' ? 'active' : ''}`}
          onClick={() => setStatusFilter('predicted')}
          style={{ cursor: 'pointer', borderLeft: '3px solid #3b82f6' }}
        >
          <span className="stat-label">{t('solutions.filter_predicted')}</span>
          <span className="stat-value">{statusCounts.predicted}</span>
        </div>
        {(searchTerm || statusFilter !== 'all') && (
          <div className="stat-card">
            <span className="stat-label">{t('solutions.filter_results')}</span>
            <span className="stat-value">{filteredSolutions.length}</span>
          </div>
        )}
      </div>

      <div className="solution-table-container">
        <div className="solution-table-wrapper">
          <DataTable
            columns={general_columns}
            data={filteredSolutions}
            defaultSortField="solution_name"
            pagination
            highlightOnHover
            responsive
            striped
            paginationPerPage={30}
            paginationRowsPerPageOptions={[30, 50, 100]}
            customStyles={{
              headRow: {
                style: {
                  backgroundColor: '#f9fafb',
                  borderBottom: '2px solid #e5e7eb',
                  fontSize: '0.875rem',
                  fontWeight: '600',
                  color: '#374151',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                },
              },
              headCells: {
                style: {
                  paddingLeft: '1rem',
                  paddingRight: '1rem',
                },
              },
              rows: {
                style: {
                  fontSize: '0.875rem',
                  color: '#1f2937',
                  '&:hover': {
                    backgroundColor: '#f9fafb',
                    cursor: 'pointer',
                  },
                },
              },
              cells: {
                style: {
                  paddingLeft: '1rem',
                  paddingRight: '1rem',
                  paddingTop: '0.75rem',
                  paddingBottom: '0.75rem',
                },
              },
            }}
            noDataComponent={
              <div className="empty-state">
                <div className="empty-icon">📋</div>
                <h3>{t('solutions.empty_title')}</h3>
                <p>
                  {searchTerm
                    ? t('solutions.empty_search', { searchTerm })
                    : t('solutions.empty_default')}
                </p>
                {!searchTerm && (
                  <Button onClick={onAddNew} className="btn btn-primary">
                    {t('solutions.create_first')}
                  </Button>
                )}
              </div>
            }
          />
        </div>
      </div>

      {/* Solution Modal */}
      <SolutionModal
        show={showModal}
        onHide={handleModalClose}
        solution={selectedSolution}
        onSave={handleModalSave}
      />
    </div>
  );

}
export default SolutionList;