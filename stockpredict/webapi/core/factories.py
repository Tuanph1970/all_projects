from abc import ABC, abstractmethod
from typing import Dict, Any
from core.exceptions import ModelCreationException


class ModelFactory(ABC):
    @abstractmethod
    def create_model(self, model_data: Dict[str, Any]) -> Any:
        pass
    
    @abstractmethod
    def get_model_type(self) -> str:
        pass


class PredictModelFactory:
    _factories: Dict[str, ModelFactory] = {}
    
    @classmethod
    def register_factory(cls, model_type: str, factory: ModelFactory):
        cls._factories[model_type] = factory
    
    @classmethod
    def create_model(cls, model_type: str, model_data: Dict[str, Any]) -> Any:
        factory = cls._factories.get(model_type)
        if not factory:
            raise ModelCreationException(model_type, f"No factory registered for model type: {model_type}")
        
        return factory.create_model(model_data)
    
    @classmethod
    def get_supported_models(cls) -> list:
        return list(cls._factories.keys())


class RNNModelFactory(ModelFactory):
    def create_model(self, model_data: Dict[str, Any]) -> Any:
        from Models.Common import create_rnn_model
        return create_rnn_model(model_data.get('model_id'), model_data)

    def get_model_type(self) -> str:
        return "RNN"


class XGBoostModelFactory(ModelFactory):
    def create_model(self, model_data: Dict[str, Any]) -> Any:
        from Models.Common import create_xgboost_model
        return create_xgboost_model(model_data.get('model_id'), model_data)

    def get_model_type(self) -> str:
        return "XGBoost"


class DataSourceFactory:
    _sources = {
        'VCI': 'VCI',
        'TCBS': 'TCBS',
        'SSI': 'SSI'
    }
    
    @classmethod
    def get_data_source(cls, source_type: str) -> str:
        if source_type not in cls._sources:
            raise ValueError(f"Unsupported data source: {source_type}")
        return cls._sources[source_type]
    
    @classmethod
    def get_supported_sources(cls) -> list:
        return list(cls._sources.keys())


PredictModelFactory.register_factory("RNN", RNNModelFactory())
PredictModelFactory.register_factory("XGBoost", XGBoostModelFactory())