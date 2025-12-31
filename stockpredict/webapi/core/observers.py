from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enum import Enum


class ModelEvent(Enum):
    MODEL_CREATED = "model_created"
    MODEL_TRAINING_STARTED = "model_training_started"
    MODEL_TRAINING_COMPLETED = "model_training_completed"
    MODEL_TRAINING_FAILED = "model_training_failed"
    MODEL_DELETED = "model_deleted"


class Observer(ABC):
    @abstractmethod
    def update(self, event: ModelEvent, data: Dict[str, Any]):
        pass


class Subject(ABC):
    def __init__(self):
        self._observers: List[Observer] = []
    
    def attach(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)
    
    def detach(self, observer: Observer):
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify(self, event: ModelEvent, data: Dict[str, Any] = None):
        for observer in self._observers:
            observer.update(event, data or {})


class ModelNotificationObserver(Observer):
    def update(self, event: ModelEvent, data: Dict[str, Any]):
        print(f"Model Notification: {event.value} - {data}")


class ModelLoggingObserver(Observer):
    def __init__(self, log_file: str = "model_events.log"):
        self.log_file = log_file
    
    def update(self, event: ModelEvent, data: Dict[str, Any]):
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f"[{timestamp}] {event.value}: {data}\n"
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write to log file: {e}")


class ModelEventPublisher(Subject):
    def __init__(self):
        super().__init__()
        self.attach(ModelNotificationObserver())
        self.attach(ModelLoggingObserver())
    
    def model_created(self, model_id: int, model_type: str, model_name: str):
        self.notify(ModelEvent.MODEL_CREATED, {
            'model_id': model_id,
            'model_type': model_type,
            'model_name': model_name
        })
    
    def model_training_started(self, model_id: int):
        self.notify(ModelEvent.MODEL_TRAINING_STARTED, {
            'model_id': model_id
        })
    
    def model_training_completed(self, model_id: int, metrics: Dict = None):
        self.notify(ModelEvent.MODEL_TRAINING_COMPLETED, {
            'model_id': model_id,
            'metrics': metrics or {}
        })
    
    def model_training_failed(self, model_id: int, error: str):
        self.notify(ModelEvent.MODEL_TRAINING_FAILED, {
            'model_id': model_id,
            'error': error
        })
    
    def model_deleted(self, model_id: int):
        self.notify(ModelEvent.MODEL_DELETED, {
            'model_id': model_id
        })