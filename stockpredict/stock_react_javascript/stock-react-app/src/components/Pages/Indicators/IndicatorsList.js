import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import indicatorService from '../../../services/indicatorService';
import './Indicators.css';

const IndicatorsList = () => {
  const { t } = useTranslation();
  const [indicators, setIndicators] = useState({
    trend: [],
    momentum: [],
    volatility: [],
    volume: [],
    support_resistance: [],
    price_transform: [],
    bill_williams: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('trend');
  const [selectedIndicator, setSelectedIndicator] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingIndicator, setEditingIndicator] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    type: 'trend',
    description: '',
    calculation_function: '',
    default_parameters: '{}'
  });
  const [formErrors, setFormErrors] = useState({});

  useEffect(() => {
    fetchAllIndicators();
  }, []);

  const fetchAllIndicators = async () => {
    try {
      setLoading(true);
      const data = await indicatorService.getAllIndicators();
      setIndicators(data);
      setError(null);
    } catch (err) {
      setError(t('indicators.error_load') + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getCategoryIcon = (category) => {
    const icons = {
      trend: '📈',
      momentum: '⚡',
      volatility: '📊',
      volume: '📦',
      support_resistance: '📐',
      price_transform: '🔄',
      bill_williams: '🐊'
    };
    return icons[category] || '📊';
  };

  const getCategoryColor = (category) => {
    const colors = {
      trend: '#3b82f6',
      momentum: '#f59e0b',
      volatility: '#ef4444',
      volume: '#10b981',
      support_resistance: '#8b5cf6',
      price_transform: '#ec4899',
      bill_williams: '#06b6d4'
    };
    return colors[category] || '#6b7280';
  };

  const getCategoryLabel = (category) => {
    const labels = {
      trend: t('indicators.category_trend'),
      momentum: t('indicators.category_momentum'),
      volatility: t('indicators.category_volatility'),
      volume: t('indicators.category_volume'),
      support_resistance: t('indicators.category_support'),
      price_transform: t('indicators.category_price'),
      bill_williams: t('indicators.category_williams')
    };
    return labels[category] || category.charAt(0).toUpperCase() + category.slice(1);
  };

  const handleAddNew = () => {
    setFormData({
      name: '',
      type: selectedCategory,
      description: '',
      calculation_function: '',
      default_parameters: '{}'
    });
    setFormErrors({});
    setShowAddModal(true);
  };

  const handleEdit = (indicator, e) => {
    e.stopPropagation();
    setEditingIndicator(indicator);
    setFormData({
      name: indicator.name,
      type: indicator.type,
      description: indicator.description,
      calculation_function: indicator.calculation_function,
      default_parameters: JSON.stringify(indicator.default_parameters, null, 2)
    });
    setFormErrors({});
    setShowEditModal(true);
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

    if (!formData.name.trim()) {
      errors.name = t('indicators.error_name_required');
    }

    if (!formData.description.trim()) {
      errors.description = t('indicators.error_description_required');
    }

    if (!formData.calculation_function.trim()) {
      errors.calculation_function = t('indicators.error_calculation_required');
    }

    // Validate JSON format for parameters
    try {
      JSON.parse(formData.default_parameters);
    } catch (e) {
      errors.default_parameters = t('indicators.error_invalid_json');
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
        ...formData,
        default_parameters: JSON.parse(formData.default_parameters)
      };

      await indicatorService.createIndicator(data);
      setShowAddModal(false);
      await fetchAllIndicators();
      setError(null);
    } catch (err) {
      setError(t('indicators.error_create') + err.message);
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
        name: formData.name,
        type: formData.type,
        description: formData.description,
        calculation_function: formData.calculation_function,
        default_parameters: JSON.parse(formData.default_parameters)
      };

      await indicatorService.updateIndicator(editingIndicator.id, data);
      setShowEditModal(false);
      setEditingIndicator(null);
      await fetchAllIndicators();
      setError(null);
    } catch (err) {
      setError(t('indicators.error_update') + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCloseModal = () => {
    setShowAddModal(false);
    setShowEditModal(false);
    setEditingIndicator(null);
    setFormData({
      name: '',
      type: 'trend',
      description: '',
      calculation_function: '',
      default_parameters: '{}'
    });
    setFormErrors({});
  };

  if (loading) {
    return (
      <div className="indicators-container">
        <div className="loading">{t('indicators.loading')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="indicators-container">
        <div className="error">{error}</div>
      </div>
    );
  }

  const currentIndicators = indicators[selectedCategory] || [];

  return (
    <div className="indicators-container">
      <div className="indicators-header">
        <div>
          <h1>{t('indicators.title')}</h1>
          <p className="subtitle">
            {t('indicators.subtitle')}
          </p>
        </div>
        <button className="add-new-button" onClick={handleAddNew}>
          {t('indicators.button_add')}
        </button>
      </div>

      {/* Category Tabs */}
      <div className="category-tabs">
        {['trend', 'momentum', 'volatility', 'volume', 'support_resistance', 'price_transform', 'bill_williams'].map((category) => (
          <button
            key={category}
            className={`category-tab ${selectedCategory === category ? 'active' : ''}`}
            onClick={() => {
              setSelectedCategory(category);
              setSelectedIndicator(null);
            }}
            style={{
              borderColor: selectedCategory === category ? getCategoryColor(category) : '#e5e7eb'
            }}
          >
            <span className="category-icon">{getCategoryIcon(category)}</span>
            <span className="category-name">
              {getCategoryLabel(category)}
            </span>
            <span className="category-count">
              {indicators[category]?.length || 0}
            </span>
          </button>
        ))}
      </div>

      {/* Indicators Grid */}
      <div className="indicators-grid">
        {currentIndicators.map((indicator) => (
          <div
            key={indicator.id}
            className={`indicator-card ${selectedIndicator?.id === indicator.id ? 'selected' : ''}`}
            onClick={() => setSelectedIndicator(indicator)}
            style={{
              borderLeftColor: getCategoryColor(selectedCategory)
            }}
          >
            <div className="indicator-header">
              <h3>{indicator.name}</h3>
              <div className="indicator-actions">
                <span
                  className="indicator-badge"
                  style={{
                    backgroundColor: getCategoryColor(selectedCategory) + '20',
                    color: getCategoryColor(selectedCategory)
                  }}
                >
                  {selectedCategory}
                </span>
                <button
                  className="edit-button"
                  onClick={(e) => handleEdit(indicator, e)}
                  title={t('indicators.tooltip_edit')}
                >
                  {t('indicators.button_edit')}
                </button>
              </div>
            </div>
            <p className="indicator-description">{indicator.description}</p>
            <div className="indicator-parameters">
              <strong>{t('indicators.info_default_params')}</strong>
              <pre>{JSON.stringify(indicator.default_parameters, null, 2)}</pre>
            </div>
          </div>
        ))}
      </div>

      {/* Selected Indicator Details */}
      {selectedIndicator && (
        <div className="indicator-details-modal" onClick={() => setSelectedIndicator(null)}>
          <div className="indicator-details-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-button" onClick={() => setSelectedIndicator(null)}>
              ✕
            </button>
            <h2>{selectedIndicator.name}</h2>
            <div className="details-section">
              <h3>{t('indicators.details_description')}</h3>
              <p>{selectedIndicator.description}</p>
            </div>
            <div className="details-section">
              <h3>{t('indicators.details_category')}</h3>
              <span
                className="category-badge-large"
                style={{
                  backgroundColor: getCategoryColor(selectedCategory),
                  color: 'white'
                }}
              >
                {getCategoryLabel(selectedCategory)}
              </span>
            </div>
            <div className="details-section">
              <h3>{t('indicators.details_default_params')}</h3>
              <pre className="parameters-display">
                {JSON.stringify(selectedIndicator.default_parameters, null, 2)}
              </pre>
            </div>
            <div className="details-section">
              <h3>{t('indicators.details_calculation')}</h3>
              <code>{selectedIndicator.calculation_function}</code>
            </div>
          </div>
        </div>
      )}

      {/* Add New Indicator Modal */}
      {showAddModal && (
        <div className="indicator-modal-overlay" onClick={handleCloseModal}>
          <div className="indicator-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('indicators.modal_add_title')}</h2>
              <button className="close-button" onClick={handleCloseModal}>✕</button>
            </div>
            <form onSubmit={handleSubmitAdd}>
              <div className="form-group">
                <label htmlFor="name">{t('indicators.field_name')}</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleFormChange}
                  className={formErrors.name ? 'error' : ''}
                  placeholder={t('indicators.placeholder_name')}
                />
                {formErrors.name && <span className="error-message">{formErrors.name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="type">{t('indicators.field_category')}</label>
                <select
                  id="type"
                  name="type"
                  value={formData.type}
                  onChange={handleFormChange}
                >
                  <option value="trend">{t('indicators.category_trend')}</option>
                  <option value="momentum">{t('indicators.category_momentum')}</option>
                  <option value="volatility">{t('indicators.category_volatility')}</option>
                  <option value="volume">{t('indicators.category_volume')}</option>
                  <option value="support_resistance">{t('indicators.category_support')}</option>
                  <option value="price_transform">{t('indicators.category_price')}</option>
                  <option value="bill_williams">{t('indicators.category_williams')}</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="description">{t('indicators.field_description')}</label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleFormChange}
                  className={formErrors.description ? 'error' : ''}
                  placeholder={t('indicators.placeholder_description')}
                  rows="3"
                />
                {formErrors.description && <span className="error-message">{formErrors.description}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="calculation_function">{t('indicators.field_calculation')}</label>
                <input
                  type="text"
                  id="calculation_function"
                  name="calculation_function"
                  value={formData.calculation_function}
                  onChange={handleFormChange}
                  className={formErrors.calculation_function ? 'error' : ''}
                  placeholder={t('indicators.placeholder_calculation')}
                />
                {formErrors.calculation_function && <span className="error-message">{formErrors.calculation_function}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="default_parameters">{t('indicators.field_default_params')}</label>
                <textarea
                  id="default_parameters"
                  name="default_parameters"
                  value={formData.default_parameters}
                  onChange={handleFormChange}
                  className={formErrors.default_parameters ? 'error' : ''}
                  placeholder={t('indicators.placeholder_default_params')}
                  rows="4"
                />
                {formErrors.default_parameters && <span className="error-message">{formErrors.default_parameters}</span>}
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={handleCloseModal}>
                  {t('indicators.button_cancel')}
                </button>
                <button type="submit" className="btn-submit">
                  {t('indicators.button_create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Indicator Modal */}
      {showEditModal && editingIndicator && (
        <div className="indicator-modal-overlay" onClick={handleCloseModal}>
          <div className="indicator-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('indicators.modal_edit_title')}</h2>
              <button className="close-button" onClick={handleCloseModal}>✕</button>
            </div>
            <form onSubmit={handleSubmitEdit}>
              <div className="form-group">
                <label htmlFor="edit-name">{t('indicators.field_name')}</label>
                <input
                  type="text"
                  id="edit-name"
                  name="name"
                  value={formData.name}
                  onChange={handleFormChange}
                  className={formErrors.name ? 'error' : ''}
                  placeholder={t('indicators.placeholder_name')}
                />
                {formErrors.name && <span className="error-message">{formErrors.name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="edit-type">{t('indicators.field_category')}</label>
                <select
                  id="edit-type"
                  name="type"
                  value={formData.type}
                  onChange={handleFormChange}
                >
                  <option value="trend">{t('indicators.category_trend')}</option>
                  <option value="momentum">{t('indicators.category_momentum')}</option>
                  <option value="volatility">{t('indicators.category_volatility')}</option>
                  <option value="volume">{t('indicators.category_volume')}</option>
                  <option value="support_resistance">{t('indicators.category_support')}</option>
                  <option value="price_transform">{t('indicators.category_price')}</option>
                  <option value="bill_williams">{t('indicators.category_williams')}</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="edit-description">{t('indicators.field_description')}</label>
                <textarea
                  id="edit-description"
                  name="description"
                  value={formData.description}
                  onChange={handleFormChange}
                  className={formErrors.description ? 'error' : ''}
                  placeholder={t('indicators.placeholder_description')}
                  rows="3"
                />
                {formErrors.description && <span className="error-message">{formErrors.description}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="edit-calculation_function">{t('indicators.field_calculation')}</label>
                <input
                  type="text"
                  id="edit-calculation_function"
                  name="calculation_function"
                  value={formData.calculation_function}
                  onChange={handleFormChange}
                  className={formErrors.calculation_function ? 'error' : ''}
                  placeholder={t('indicators.placeholder_calculation')}
                />
                {formErrors.calculation_function && <span className="error-message">{formErrors.calculation_function}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="edit-default_parameters">{t('indicators.field_default_params')}</label>
                <textarea
                  id="edit-default_parameters"
                  name="default_parameters"
                  value={formData.default_parameters}
                  onChange={handleFormChange}
                  className={formErrors.default_parameters ? 'error' : ''}
                  placeholder={t('indicators.placeholder_default_params')}
                  rows="4"
                />
                {formErrors.default_parameters && <span className="error-message">{formErrors.default_parameters}</span>}
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={handleCloseModal}>
                  {t('indicators.button_cancel')}
                </button>
                <button type="submit" className="btn-submit">
                  {t('indicators.button_update')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default IndicatorsList;
