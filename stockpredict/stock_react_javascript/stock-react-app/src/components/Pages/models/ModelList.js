import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import './Models.css';
import ModelService from "../../../services/modelService";
import httpClient from "../../../services/httpClient";
import { API_ENDPOINTS } from "../../../constants/api";

const ModelList = () => {
    const [modelListData, setModelListData] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [selectedModel, setSelectedModel] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [editingModel, setEditingModel] = useState(null);
    const [selectedType, setSelectedType] = useState('all');

    // Form states
    const [modelParam, setModelParam] = useState([]);
    const [paramOptions, setParamOptions] = useState([]);
    const [paramDefaultValues, setParamDefaultValues] = useState([]);
    const [currentParam, setCurrentParam] = useState([]);
    const [currentDefaultValues, setCurrentDefaultValues] = useState([]);
    const [modelTypeList, setModelTypeList] = useState([]);
    const [modelType, setModelType] = useState("");
    const [formErrors, setFormErrors] = useState({});

    const { register, handleSubmit, reset, formState: { errors } } = useForm();

    // Helper function to safely format dates
    const formatDate = (dateValue, includeTime = false) => {
        if (!dateValue) return 'N/A';
        try {
            const date = new Date(dateValue);
            if (isNaN(date.getTime())) return 'N/A';
            return includeTime ? date.toLocaleString() : date.toLocaleDateString();
        } catch (error) {
            return 'N/A';
        }
    };

    useEffect(() => {
        loadInitialData();
    }, []);

    const loadInitialData = async () => {
        setIsLoading(true);
        try {
            await Promise.all([
                getModelList(),
                getModelParams(),
                getOptionsFromParams(),
                getModelParamsDefaultValues(),
                getModelTypes()
            ]);
            setError(null);
        } catch (err) {
            setError('Failed to load data: ' + err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const getModelList = async () => {
        try {
            const result = await ModelService.getAllModels();
            if (result.success) {
                setModelListData(result.data);
            } else {
                console.error('Failed to fetch models:', result.error);
            }
        } catch (error) {
            console.error('Error in getModelList:', error);
        }
    };

    const getModelParams = async () => {
        const result = await ModelService.getModelParameters();
        if (result.success) {
            setModelParam(result.data);
        } else {
            console.error('Failed to fetch model parameters:', result.error);
        }
    };

    const getOptionsFromParams = async () => {
        const result = await ModelService.getParameterOptions();
        if (result.success) {
            setParamOptions(result.data);
        } else {
            console.error('Failed to fetch parameter options:', result.error);
        }
    };

    const getModelParamsDefaultValues = async () => {
        const result = await ModelService.getParameterDefaultValues();
        if (result.success) {
            setParamDefaultValues(result.data);
        } else {
            console.error('Failed to fetch parameter default values:', result.error);
        }
    };

    const getModelTypes = async () => {
        try {
            const result = await ModelService.getModelTypes();
            if (result.success) {
                setModelTypeList(result.data);
            } else {
                console.error('Failed to fetch model types:', result.error);
            }
        } catch (error) {
            console.error('Error fetching model types:', error);
        }
    };

    const getTypeColor = (type) => {
        const colors = {
            'LSTM': '#3b82f6',
            'GRU': '#f59e0b',
            'CNN': '#ef4444',
            'TRANSFORMER': '#10b981',
            'default': '#6b7280'
        };
        return colors[type?.toUpperCase()] || colors.default;
    };

    const getTypeIcon = (type) => {
        const icons = {
            'LSTM': '🧠',
            'GRU': '⚡',
            'CNN': '🔍',
            'TRANSFORMER': '🤖',
            'default': '📊'
        };
        return icons[type?.toUpperCase()] || icons.default;
    };

    const handleAddNew = () => {
        setModelType("");
        setCurrentParam([]);
        setCurrentDefaultValues([]);
        setFormErrors({});
        reset({
            model_name: '',
            model_type: ''
        });
        setShowAddModal(true);
    };

    const handleEdit = async (model, e) => {
        e.stopPropagation();
        try {
            setIsLoading(true);

            // Fetch the full model configuration from the backend
            const result = await ModelService.getModelById(model.id);

            if (result.success && result.data) {
                const fullModelData = result.data;
                setEditingModel(model);
                setModelType(model.model_type);
                // Pass true to preserve existing values (don't apply defaults when editing)
                modelTypeOnChange(model.model_type, true);

                // Reset form with the full configuration data
                reset({
                    model_name: model.model_name,
                    ...fullModelData
                });

                setFormErrors({});
                setShowEditModal(true);
            } else {
                setError('Failed to load model configuration: ' + (result.error || 'Unknown error'));
            }
        } catch (err) {
            setError('Failed to load model configuration: ' + err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleDelete = async (model, e) => {
        e.stopPropagation();
        if (window.confirm(`Are you sure you want to delete "${model.model_name}"?`)) {
            try {
                setIsLoading(true);
                const result = await ModelService.deleteModel(model.id);
                if (result.success) {
                    await getModelList();
                    setError(null);
                } else {
                    setError('Failed to delete model: ' + result.error);
                }
            } catch (err) {
                setError('Failed to delete model: ' + err.message);
            } finally {
                setIsLoading(false);
            }
        }
    };

    const handleCloseModal = () => {
        setShowAddModal(false);
        setShowEditModal(false);
        setEditingModel(null);
        setModelType("");
        setCurrentParam([]);
        setCurrentDefaultValues([]);
        setFormErrors({});
        reset();
    };

    const modelTypeOnChange = (selected_item, preserveExistingValues = false) => {
        setModelType(selected_item);
        let objParam = modelParam.filter(param => param.model_type_ === selected_item);
        if (objParam.length > 0) {
            setCurrentParam(Object.entries(objParam[0]));
        }
        let objDefaultValue = paramDefaultValues.filter(defautValue => defautValue.model_type_ === selected_item);
        if (objDefaultValue.length > 0) {
            const defaults = objDefaultValue[0];
            setCurrentDefaultValues(defaults);

            // Apply default values to form when adding new model (not preserving existing)
            if (!preserveExistingValues && defaults) {
                // Create a clean defaults object excluding the model_type_ field
                const formDefaults = {};
                Object.keys(defaults).forEach(key => {
                    if (key !== 'model_type_') {
                        formDefaults[key] = defaults[key];
                    }
                });
                // Reset form with current model_name and model_type, plus the defaults
                reset(currentValues => ({
                    ...currentValues,
                    model_type: selected_item,
                    ...formDefaults
                }));
            }
        }
    };

    const getOptionsFromParam = (strParam) => {
        let objParam = paramOptions.filter(paramOption => paramOption.param_name === strParam);
        if (objParam.length > 0) {
            let optionP = objParam[0];
            let options = optionP['options'].split(',');
            return options;
        } else {
            return null;
        }
    };

    const getDefaultFieldValue = (fieldName) => {
        return currentDefaultValues[fieldName];
    };

    const renderControl = (data) => {
        if (data[1].length > 0) {
            if (data[1] === "text") {
                return (
                    <div className="form-group" key={data[0]}>
                        <label htmlFor={data[0]}>{data[0]}</label>
                        <input
                            {...register(data[0], { required: true })}
                            type="text"
                            id={data[0]}
                            className={formErrors[data[0]] ? 'error' : ''}
                        />
                        {formErrors[data[0]] && <span className="error-message">{formErrors[data[0]]}</span>}
                    </div>
                );
            } else if (data[1] === "checkbox") {
                return (
                    <div className="form-group checkbox-group" key={data[0]}>
                        <input
                            {...register(data[0], { required: false })}
                            type="checkbox"
                            id={data[0]}
                        />
                        <label htmlFor={data[0]}>{data[0]}</label>
                    </div>
                );
            } else if (data[1] === "select") {
                return (
                    <div className="form-group" key={data[0]}>
                        <label htmlFor={data[0]}>{data[0]}</label>
                        <select
                            {...register(data[0])}
                            id={data[0]}
                        >
                            {getOptionsFromParam(data[0])?.map((option_item, idx) => (
                                <option key={idx} value={option_item}>
                                    {option_item}
                                </option>
                            ))}
                        </select>
                    </div>
                );
            }
        }
        return null;
    };

    const validateForm = () => {
        const errors = {};
        if (!modelType) {
            errors.model_type = 'Model type is required';
        }
        setFormErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleSubmitAdd = async (data) => {
        if (!validateForm()) {
            return;
        }

        try {
            setIsLoading(true);
            const result = await httpClient.post(API_ENDPOINTS.MODEL_BY_TYPE(modelType.toLowerCase()), data);

            if (!result.success) {
                throw new Error(result.error?.message || 'Failed to create model');
            }

            setShowAddModal(false);
            await getModelList();
            setError(null);
        } catch (err) {
            setError('Failed to create model: ' + err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmitEdit = async (data) => {
        if (!validateForm()) {
            return;
        }

        try {
            setIsLoading(true);
            data['model_id'] = editingModel.id;
            const result = await httpClient.put(API_ENDPOINTS.MODEL_BY_TYPE(modelType.toLowerCase()), data);

            if (!result.success) {
                throw new Error(result.error?.message || 'Failed to update model');
            }

            setShowEditModal(false);
            setEditingModel(null);
            await getModelList();
            setError(null);
        } catch (err) {
            setError('Failed to update model: ' + err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const uniqueTypes = ['all', ...new Set(modelListData.map(m => m.model_type))];
    const filteredModels = selectedType === 'all'
        ? modelListData
        : modelListData.filter(m => m.model_type === selectedType);

    if (isLoading && modelListData.length === 0) {
        return (
            <div className="models-container">
                <div className="loading">Loading models...</div>
            </div>
        );
    }

    return (
        <div className="models-container">
            <div className="models-header">
                <div>
                    <h1>Prediction Models</h1>
                    <p className="subtitle">
                        Manage machine learning models for stock price prediction
                    </p>
                </div>
                <button className="add-new-button" onClick={handleAddNew}>
                    ➕ Add New Model
                </button>
            </div>

            {error && <div className="error-banner">{error}</div>}

            {/* Type Filter Tabs */}
            <div className="type-tabs">
                {uniqueTypes.map((type) => (
                    <button
                        key={type}
                        className={`type-tab ${selectedType === type ? 'active' : ''}`}
                        onClick={() => {
                            setSelectedType(type);
                            setSelectedModel(null);
                        }}
                        style={{
                            borderColor: selectedType === type ? getTypeColor(type) : '#e5e7eb'
                        }}
                    >
                        <span className="type-icon">{type === 'all' ? '📋' : getTypeIcon(type)}</span>
                        <span className="type-name">
                            {type === 'all' ? 'All Models' : type}
                        </span>
                        <span className="type-count">
                            {type === 'all' ? modelListData.length : modelListData.filter(m => m.model_type === type).length}
                        </span>
                    </button>
                ))}
            </div>

            {/* Models Grid */}
            <div className="models-grid">
                {filteredModels.map((model) => (
                    <div
                        key={model.id}
                        className={`model-card ${selectedModel?.id === model.id ? 'selected' : ''}`}
                        onClick={() => setSelectedModel(model)}
                        style={{
                            borderLeftColor: getTypeColor(model.model_type)
                        }}
                    >
                        <div className="model-header">
                            <h3>{model.model_name}</h3>
                            <div className="model-actions">
                                <span
                                    className="model-badge"
                                    style={{
                                        backgroundColor: getTypeColor(model.model_type) + '20',
                                        color: getTypeColor(model.model_type)
                                    }}
                                >
                                    {model.model_type}
                                </span>
                                <button
                                    className="edit-button"
                                    onClick={(e) => handleEdit(model, e)}
                                    title="Edit model"
                                >
                                    ✏️ Edit
                                </button>
                                <button
                                    className="delete-button"
                                    onClick={(e) => handleDelete(model, e)}
                                    title="Delete model"
                                >
                                    🗑️ Delete
                                </button>
                            </div>
                        </div>
                        <div className="model-info">
                            <div className="info-item">
                                <span className="info-label">Sub Type:</span>
                                <span className="info-value">{model.model_sub_type || 'N/A'}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Created:</span>
                                <span className="info-value">{formatDate(model.created_at)}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Updated:</span>
                                <span className="info-value">{formatDate(model.updated_at)}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Created By:</span>
                                <span className="info-value">{model.created_by}</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {filteredModels.length === 0 && (
                <div className="empty-state">
                    <p>No models found. Create your first model to get started!</p>
                </div>
            )}

            {/* Selected Model Details Modal */}
            {selectedModel && (
                <div className="model-details-modal" onClick={() => setSelectedModel(null)}>
                    <div className="model-details-content" onClick={(e) => e.stopPropagation()}>
                        <button className="close-button" onClick={() => setSelectedModel(null)}>
                            ✕
                        </button>
                        <h2>{selectedModel.model_name}</h2>
                        <div className="details-section">
                            <h3>Model Type</h3>
                            <span
                                className="type-badge-large"
                                style={{
                                    backgroundColor: getTypeColor(selectedModel.model_type),
                                    color: 'white'
                                }}
                            >
                                {selectedModel.model_type}
                            </span>
                        </div>
                        <div className="details-section">
                            <h3>Model Sub Type</h3>
                            <p>{selectedModel.model_sub_type || 'N/A'}</p>
                        </div>
                        <div className="details-section">
                            <h3>Created Date</h3>
                            <p>{formatDate(selectedModel.created_at, true)}</p>
                        </div>
                        <div className="details-section">
                            <h3>Updated Date</h3>
                            <p>{formatDate(selectedModel.updated_at, true)}</p>
                        </div>
                        <div className="details-section">
                            <h3>Created By</h3>
                            <p>{selectedModel.created_by}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Add New Model Modal */}
            {showAddModal && (
                <div className="model-modal-overlay" onClick={handleCloseModal}>
                    <div className="model-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Add New Model</h2>
                            <button className="close-button" onClick={handleCloseModal}>✕</button>
                        </div>
                        <form onSubmit={handleSubmit(handleSubmitAdd)}>
                            <div className="form-group">
                                <label htmlFor="model_name">Model Name *</label>
                                <input
                                    type="text"
                                    id="model_name"
                                    {...register('model_name', { required: true })}
                                    placeholder="Enter model name"
                                    className={errors.model_name ? 'error' : ''}
                                />
                                {errors.model_name && <span className="error-message">Model name is required</span>}
                            </div>

                            <div className="form-group">
                                <label htmlFor="model_type">Model Type *</label>
                                <select
                                    id="model_type"
                                    {...register("model_type")}
                                    onChange={(e) => modelTypeOnChange(e.target.value)}
                                    value={modelType}
                                    className={formErrors.model_type ? 'error' : ''}
                                >
                                    <option value="">Select a model type</option>
                                    {modelTypeList.map((data, index) => (
                                        <option key={index} value={data.name}>
                                            {data.name}
                                        </option>
                                    ))}
                                </select>
                                {formErrors.model_type && <span className="error-message">{formErrors.model_type}</span>}
                            </div>

                            {currentParam.map((data) => renderControl(data))}

                            <div className="modal-actions">
                                <button type="button" className="btn-cancel" onClick={handleCloseModal}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn-submit">
                                    Create Model
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Edit Model Modal */}
            {showEditModal && editingModel && (
                <div className="model-modal-overlay" onClick={handleCloseModal}>
                    <div className="model-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Edit Model</h2>
                            <button className="close-button" onClick={handleCloseModal}>✕</button>
                        </div>
                        <form onSubmit={handleSubmit(handleSubmitEdit)}>
                            <div className="form-group">
                                <label htmlFor="edit_model_name">Model Name *</label>
                                <input
                                    type="text"
                                    id="edit_model_name"
                                    {...register('model_name', { required: true })}
                                    placeholder="Enter model name"
                                    className={errors.model_name ? 'error' : ''}
                                />
                                {errors.model_name && <span className="error-message">Model name is required</span>}
                            </div>

                            <div className="form-group">
                                <label htmlFor="edit_model_type">Model Type</label>
                                <div className="readonly-field">{modelType}</div>
                            </div>

                            {currentParam.map((data) => renderControl(data))}

                            <div className="modal-actions">
                                <button type="button" className="btn-cancel" onClick={handleCloseModal}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn-submit">
                                    Update Model
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ModelList;
