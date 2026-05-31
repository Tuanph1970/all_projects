import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import timeSeriesService from '../../../services/timeSeriesService';
import indicatorService from '../../../services/indicatorService';
import './TimeSeries.css';

const TimeSeriesList = () => {
  const { t } = useTranslation();
  const [timeSeries, setTimeSeries] = useState([]);
  const [indicators, setIndicators] = useState({
    trend: [],
    momentum: [],
    volatility: [],
    volume: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingSeries, setEditingSeries] = useState(null);
  const [formData, setFormData] = useState({
    series_name: '',
    indicator_id: '',
    end_date: ''
  });
  const [formErrors, setFormErrors] = useState({});

  useEffect(() => {
    fetchAllData();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount
  }, []);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      const [timeSeriesData, indicatorsData] = await Promise.all([
        timeSeriesService.getAllTimeSeries(),
        indicatorService.getAllIndicators()
      ]);
      setTimeSeries(timeSeriesData);
      setIndicators(indicatorsData);
      setError(null);
    } catch (err) {
      setError(t('timeseries.error_load_data') + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getCategoryIcon = (category) => {
    const icons = {
      trend: '📈',
      momentum: '⚡',
      volatility: '📊',
      volume: '📦'
    };
    return icons[category] || '📊';
  };

  const getCategoryColor = (category) => {
    const colors = {
      trend: '#3b82f6',
      momentum: '#f59e0b',
      volatility: '#ef4444',
      volume: '#10b981'
    };
    return colors[category] || '#6b7280';
  };

  const handleAddNew = () => {
    setFormData({
      series_name: '',
      indicator_id: '',
      end_date: ''
    });
    setFormErrors({});
    setShowAddModal(true);
  };

  const handleEdit = (series, e) => {
    e.stopPropagation();
    setEditingSeries(series);
    setFormData({
      series_name: series.series_name,
      indicator_id: series.indicator_id,
      end_date: series.end_date || ''
    });
    setFormErrors({});
    setShowEditModal(true);
  };

  const handleDelete = async (seriesId, e) => {
    e.stopPropagation();
    if (window.confirm(t('timeseries.confirm_delete'))) {
      try {
        setLoading(true);
        await timeSeriesService.deleteTimeSeries(seriesId);
        await fetchAllData();
        setError(null);
      } catch (err) {
        setError(t('timeseries.error_delete') + err.message);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error for this field
    if (formErrors[name]) {
      setFormErrors(prev => ({
        ...prev,
        [name]: null
      }));
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.series_name.trim()) {
      errors.series_name = t('timeseries.error_name_required');
    }

    if (!formData.indicator_id) {
      errors.indicator_id = t('timeseries.error_indicator_required');
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmitAdd = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);
      const data = {
        series_name: formData.series_name,
        indicator_id: parseInt(formData.indicator_id),
        end_date: formData.end_date || null,
        status: 1,
        created_date: new Date().toISOString().substring(0, 10),
        created_by: 0
      };

      await timeSeriesService.createTimeSeries(data);
      setShowAddModal(false);
      await fetchAllData();
      setError(null);
    } catch (err) {
      setError(t('timeseries.error_create') + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitEdit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);
      const data = {
        id: editingSeries.id,
        series_name: formData.series_name,
        indicator_id: parseInt(formData.indicator_id),
        end_date: formData.end_date || null,
        updated_date: new Date().toISOString().substring(0, 10)
      };

      await timeSeriesService.updateTimeSeries(data);
      setShowEditModal(false);
      setEditingSeries(null);
      await fetchAllData();
      setError(null);
    } catch (err) {
      setError(t('timeseries.error_update') + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCloseModal = () => {
    setShowAddModal(false);
    setShowEditModal(false);
    setEditingSeries(null);
    setFormData({
      series_name: '',
      indicator_id: '',
      end_date: ''
    });
    setFormErrors({});
  };

  // Get all indicators as a flat list for dropdown
  // eslint-disable-next-line no-unused-vars
  const getAllIndicatorsFlat = () => {
    const allIndicators = [];
    Object.keys(indicators).forEach(category => {
      indicators[category].forEach(indicator => {
        allIndicators.push({
          ...indicator,
          category
        });
      });
    });
    return allIndicators;
  };

  if (loading && timeSeries.length === 0) {
    return (
      <div className="timeseries-container">
        <div className="loading">{t('timeseries.loading')}</div>
      </div>
    );
  }

  return (
    <div className="timeseries-container">
      <div className="timeseries-header">
        <div>
          <h1>{t('timeseries.title')}</h1>
          <p className="subtitle">
            {t('timeseries.subtitle')}
          </p>
        </div>
        <button className="add-new-button" onClick={handleAddNew}>
          {t('timeseries.button_add')}
        </button>
      </div>

      {error && (
        <div className="error">{error}</div>
      )}

      {/* Time Series Grid */}
      <div className="timeseries-grid">
        {timeSeries.map((series) => (
          <div
            key={series.id}
            className="timeseries-card"
            style={{
              borderLeftColor: getCategoryColor(series.indicator_type)
            }}
          >
            <div className="timeseries-header-content">
              <h3>{series.series_name}</h3>
              <div className="timeseries-actions">
                <span
                  className={`timeseries-badge badge-${series.indicator_type}`}
                >
                  {getCategoryIcon(series.indicator_type)} {series.indicator_type}
                </span>
              </div>
            </div>
            <p className="timeseries-description">
              <strong>{t('timeseries.label_indicator')}</strong> {series.indicator_name}
            </p>
            <div className="timeseries-info">
              <div className="timeseries-info-row">
                <strong>{t('timeseries.label_end_date_inline')}</strong>
                <span>{series.end_date || t('timeseries.not_set')}</span>
              </div>
              <div className="timeseries-info-row">
                <strong>{t('timeseries.label_created')}</strong>
                <span>{series.created_date}</span>
              </div>
              <div className="timeseries-info-row">
                <strong>{t('timeseries.label_parameters')}</strong>
                <span>{JSON.stringify(series.default_parameters)}</span>
              </div>
            </div>
            <div className="timeseries-actions" style={{ marginTop: '12px', justifyContent: 'flex-end' }}>
              <button
                className="edit-button"
                onClick={(e) => handleEdit(series, e)}
                title={t('timeseries.tooltip_edit')}
              >
                {t('timeseries.button_edit')}
              </button>
              <button
                className="delete-button"
                onClick={(e) => handleDelete(series.id, e)}
                title={t('timeseries.tooltip_delete')}
              >
                {t('timeseries.button_delete')}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Add New Time Series Modal */}
      {showAddModal && (
        <div className="timeseries-modal-overlay" onClick={handleCloseModal}>
          <div className="timeseries-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('timeseries.modal_add_title')}</h2>
              <button className="close-button" onClick={handleCloseModal}>✕</button>
            </div>
            <form onSubmit={handleSubmitAdd}>
              <div className="form-group">
                <label htmlFor="series_name">{t('timeseries.field_name')}</label>
                <input
                  type="text"
                  id="series_name"
                  name="series_name"
                  value={formData.series_name}
                  onChange={handleFormChange}
                  className={formErrors.series_name ? 'error' : ''}
                  placeholder={t('timeseries.placeholder_name')}
                />
                {formErrors.series_name && <span className="error-message">{formErrors.series_name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="indicator_id">{t('timeseries.field_indicator')}</label>
                <select
                  id="indicator_id"
                  name="indicator_id"
                  value={formData.indicator_id}
                  onChange={handleFormChange}
                  className={formErrors.indicator_id ? 'error' : ''}
                >
                  <option value="">{t('timeseries.option_select')}</option>
                  {Object.keys(indicators).map(category => (
                    <optgroup key={category} label={category.toUpperCase()}>
                      {indicators[category].map(indicator => (
                        <option key={indicator.id} value={indicator.id}>
                          {indicator.name} - {indicator.description}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
                {formErrors.indicator_id && <span className="error-message">{formErrors.indicator_id}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="end_date">{t('timeseries.field_end_date')}</label>
                <input
                  type="date"
                  id="end_date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleFormChange}
                  placeholder={t('timeseries.placeholder_end_date')}
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={handleCloseModal}>
                  {t('timeseries.button_cancel')}
                </button>
                <button type="submit" className="btn-submit">
                  {t('timeseries.button_create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Time Series Modal */}
      {showEditModal && editingSeries && (
        <div className="timeseries-modal-overlay" onClick={handleCloseModal}>
          <div className="timeseries-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('timeseries.modal_edit_title')}</h2>
              <button className="close-button" onClick={handleCloseModal}>✕</button>
            </div>
            <form onSubmit={handleSubmitEdit}>
              <div className="form-group">
                <label htmlFor="edit-series_name">{t('timeseries.field_name')}</label>
                <input
                  type="text"
                  id="edit-series_name"
                  name="series_name"
                  value={formData.series_name}
                  onChange={handleFormChange}
                  className={formErrors.series_name ? 'error' : ''}
                  placeholder={t('timeseries.placeholder_name')}
                />
                {formErrors.series_name && <span className="error-message">{formErrors.series_name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="edit-indicator_id">{t('timeseries.field_indicator')}</label>
                <select
                  id="edit-indicator_id"
                  name="indicator_id"
                  value={formData.indicator_id}
                  onChange={handleFormChange}
                  className={formErrors.indicator_id ? 'error' : ''}
                >
                  <option value="">{t('timeseries.option_select')}</option>
                  {Object.keys(indicators).map(category => (
                    <optgroup key={category} label={category.toUpperCase()}>
                      {indicators[category].map(indicator => (
                        <option key={indicator.id} value={indicator.id}>
                          {indicator.name} - {indicator.description}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
                {formErrors.indicator_id && <span className="error-message">{formErrors.indicator_id}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="edit-end_date">{t('timeseries.field_end_date')}</label>
                <input
                  type="date"
                  id="edit-end_date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleFormChange}
                  placeholder={t('timeseries.placeholder_end_date')}
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={handleCloseModal}>
                  {t('timeseries.button_cancel')}
                </button>
                <button type="submit" className="btn-submit">
                  {t('timeseries.button_update')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimeSeriesList;
