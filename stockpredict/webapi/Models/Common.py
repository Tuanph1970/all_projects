"""
Common.py v2 - Backward Compatibility Layer
This module provides backward compatibility for existing code while delegating to the new unified architecture.

MIGRATION NOTES:
1. This file maintains the same function signatures as the original Common.py
2. All functions now delegate to UnifiedModelService
3. Gradually migrate calling code to use UnifiedModelService directly
4. Once migration is complete, this file can be deprecated
"""
import os
import json
from typing import Dict, List, Optional
from core.unified_model_service import UnifiedModelService
from core.model_registry import ModelRegistry
from repositories.model_repository import ModelRepository
from repositories.all_models_repository import AllModelsRepository


# Initialize unified service (singleton pattern)
_unified_service = UnifiedModelService()


def get_all_predict_model() -> List[Dict]:
    """
    Get all available prediction model types from database.

    Returns:
        List of dictionaries with model types and sub-models
    """
    try:
        repo = AllModelsRepository()
        return repo.get_all_models_with_subtypes(active_only=True)
    except Exception as e:
        print(f"Error fetching model types from database: {e}")
        return []


def get_model_parameters_by_id(model_id: int, model_name: str, model_type: str) -> Dict:
    """
    Get model parameters by ID (DEPRECATED - use UnifiedModelService.get_model_parameters_by_id).

    Args:
        model_id: Model instance ID
        model_name: Model name (not used in new architecture)
        model_type: Model type (not used in new architecture)

    Returns:
        Model configuration parameters
    """
    return _unified_service.get_model_parameters_by_id(model_id)


def get_model_parameters(model: str) -> Dict:
    """
    Get default parameters for a model type.

    Args:
        model: Model type name

    Returns:
        Default configuration parameters
    """
    return _unified_service.get_model_parameters(model)


# ==================== CREATE MODEL FUNCTIONS ====================
# These functions are now unified - they all delegate to the same create_model method

def create_rnn_model(model_id: int, data: Dict) -> Dict:
    """Create RNN model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('RNN', model_id, data)


def create_blockrnn_model(model_id: int, data: Dict) -> Dict:
    """Create BlockRNN model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('BlockRNN', model_id, data)


def create_catboost_model(model_id: int, data: Dict) -> Dict:
    """Create CatBoost model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('CatBoost', model_id, data)


def create_dlinear_model(model_id: int, data: Dict) -> Dict:
    """Create DLinear model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('DLinear', model_id, data)


def create_lightgbm_model(model_id: int, data: Dict) -> Dict:
    """Create LightGBM model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('LightGBM', model_id, data)


def create_nbeats_model(model_id: int, data: Dict) -> Dict:
    """Create NBeats model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('NBeats', model_id, data)


def create_nhits_model(model_id: int, data: Dict) -> Dict:
    """Create NHits model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('NHits', model_id, data)


def create_tcn_model(model_id: int, data: Dict) -> Dict:
    """Create TCN model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('TCN', model_id, data)


def create_tft_model(model_id: int, data: Dict) -> Dict:
    """Create TFT model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('TFT', model_id, data)


def create_nlinear_model(model_id: int, data: Dict) -> Dict:
    """Create NLinear model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('NLinear', model_id, data)


def create_tide_model(model_id: int, data: Dict) -> Dict:
    """Create TiDE model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('TiDE', model_id, data)


def create_randomforest_model(model_id: int, data: Dict) -> Dict:
    """Create RandomForest model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('RandomForest', model_id, data)


def create_xgboost_model(model_id: int, data: Dict) -> Dict:
    """Create XGBoost model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('XGBoost', model_id, data)


def create_transformer_model(model_id: int, data: Dict) -> Dict:
    """Create Transformer model (DEPRECATED - use UnifiedModelService.create_model)."""
    return _create_model_generic('Transformer', model_id, data)


# ==================== SAVE MODEL FUNCTIONS ====================
# These functions are now unified - they all delegate to the same save_model method

def save_rnn_model(data: Dict) -> Dict:
    """Save RNN model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('RNN', data)


def save_blockrnn_model(data: Dict) -> Dict:
    """Save BlockRNN model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('BlockRNN', data)


def save_catboost_model(data: Dict) -> Dict:
    """Save CatBoost model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('CatBoost', data)


def save_dlinear_model(data: Dict) -> Dict:
    """Save DLinear model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('DLinear', data)


def save_lightgbm_model(data: Dict) -> Dict:
    """Save LightGBM model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('LightGBM', data)


def save_nbeats_model(data: Dict) -> Dict:
    """Save NBeats model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('NBeats', data)


def save_nhits_model(data: Dict) -> Dict:
    """Save NHits model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('NHits', data)


def save_tcn_model(data: Dict) -> Dict:
    """Save TCN model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('TCN', data)


def save_tft_model(data: Dict) -> Dict:
    """Save TFT model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('TFT', data)


def save_nlinear_model(data: Dict) -> Dict:
    """Save NLinear model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('NLinear', data)


def save_tide_model(data: Dict) -> Dict:
    """Save TiDE model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('TiDE', data)


def save_randomforest_model(data: Dict) -> Dict:
    """Save RandomForest model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('RandomForest', data)


def save_xgboost_model(data: Dict) -> Dict:
    """Save XGBoost model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('XGBoost', data)


def save_transformer_model(data: Dict) -> Dict:
    """Save Transformer model (DEPRECATED - use UnifiedModelService.save_model)."""
    return _save_model_generic('Transformer', data)


# ==================== HELPER FUNCTIONS ====================

def _create_model_generic(model_type: str, model_id: int, data: Dict) -> Dict:
    """
    Generic create model function that delegates to UnifiedModelService.

    Args:
        model_type: Type of model
        model_id: Model ID (ignored in new architecture, generated automatically)
        data: Model configuration data

    Returns:
        Model configuration parameters
    """
    # Extract common fields
    model_name = data.get('model_name', f'{model_type}_Model')
    user_id = data.get('user_id', 'default_user')
    model_sub_type = data.get('model_sub_type')

    # Remove non-configuration fields
    config = {k: v for k, v in data.items()
             if k not in ['model_id', 'model_name', 'user_id', 'model_sub_type', 'model_type']}

    # Create model using unified service
    result = _unified_service.create_model(
        model_type=model_type,
        model_sub_type=model_sub_type,
        model_name=model_name,
        user_id=user_id,
        config=config
    )

    return result['configuration']


def _save_model_generic(model_type: str, data: Dict) -> Dict:
    """
    Generic save model function that delegates to UnifiedModelService.

    Args:
        model_type: Type of model
        data: Model data including model_id and configuration

    Returns:
        Updated model configuration parameters
    """
    model_id = data['model_id']

    # Remove non-configuration fields
    config = {k: v for k, v in data.items()
             if k not in ['model_id', 'model_name', 'user_id', 'model_sub_type', 'model_type']}

    # Save model using unified service
    return _unified_service.save_model(model_id, config)


# ==================== MODEL PARAMETER DETAIL FUNCTIONS ====================

def getModelParameterDetail(model_type: str) -> List[Dict]:
    """
    Get detailed parameter information for a model type.

    Args:
        model_type: Type of model

    Returns:
        List of parameter details with field types and names
    """
    ret = []
    params = get_model_parameters(model_type)
    model_repo = ModelRepository()

    for param_name in params.keys():
        query = "SELECT field_type, vn_name FROM tbl_dynamic_field WHERE field_name = %s"
        result = model_repo.execute_query(query, (param_name,))

        if result:
            field_info = result[0]
            param_info = {
                'param_name': param_name,
                'field_type': field_info['field_type'],
                'vn_name': field_info['vn_name']
            }
        else:
            param_info = {
                'param_name': param_name,
                'field_type': '',
                'vn_name': ''
            }
        ret.append(param_info)

    return ret


def getModelParameterFields(model_type: str) -> List[Dict]:
    """
    Get parameter fields for a model type (same as getModelParameterDetail).

    Args:
        model_type: Type of model

    Returns:
        List of parameter fields
    """
    return getModelParameterDetail(model_type)
