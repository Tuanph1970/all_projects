from abc import ABC, abstractmethod
from typing import Dict, Any, List
from core.exceptions import ModelCreationException


class Command(ABC):
    @abstractmethod
    def execute(self) -> Any:
        pass
    
    @abstractmethod
    def undo(self) -> Any:
        pass


class CreateModelCommand(Command):
    def __init__(self, model_service, model_name: str, model_type: str, 
                 model_sub_type: str = None, parameters: Dict = None):
        self.model_service = model_service
        self.model_name = model_name
        self.model_type = model_type
        self.model_sub_type = model_sub_type
        self.parameters = parameters
        self.created_model_id = None
    
    def execute(self) -> Dict:
        result = self.model_service.create_model(
            model_name=self.model_name,
            model_type=self.model_type,
            model_sub_type=self.model_sub_type,
            parameters=self.parameters
        )
        self.created_model_id = result['model_id']
        return result
    
    def undo(self) -> bool:
        if self.created_model_id:
            return self.model_service.delete_model(self.created_model_id)
        return False


class DeleteModelCommand(Command):
    def __init__(self, model_service, model_id: int):
        self.model_service = model_service
        self.model_id = model_id
        self.backup_model_data = None
    
    def execute(self) -> bool:
        self.backup_model_data = self.model_service.get_model_by_id(self.model_id)
        return self.model_service.delete_model(self.model_id)
    
    def undo(self) -> Dict:
        if self.backup_model_data:
            return self.model_service.create_model(
                model_name=self.backup_model_data['model_name'],
                model_type=self.backup_model_data['model_type'],
                model_sub_type=self.backup_model_data.get('model_sub_type'),
                parameters=self.backup_model_data.get('parameters', {})
            )
        return {}


class UpdateModelCommand(Command):
    def __init__(self, model_service, model_id: int, **update_data):
        self.model_service = model_service
        self.model_id = model_id
        self.update_data = update_data
        self.previous_data = None
    
    def execute(self) -> bool:
        self.previous_data = self.model_service.get_model_by_id(self.model_id)
        return self.model_service.update_model(self.model_id, **self.update_data)
    
    def undo(self) -> bool:
        if self.previous_data:
            return self.model_service.update_model(
                self.model_id,
                model_name=self.previous_data.get('model_name'),
                model_type=self.previous_data.get('model_type'),
                model_sub_type=self.previous_data.get('model_sub_type'),
                parameters=self.previous_data.get('parameters', {})
            )
        return False


class ModelCommandInvoker:
    def __init__(self):
        self.history: List[Command] = []
        self.current_position = -1
    
    def execute_command(self, command: Command) -> Any:
        result = command.execute()
        
        self.history = self.history[:self.current_position + 1]
        self.history.append(command)
        self.current_position += 1
        
        return result
    
    def undo(self) -> Any:
        if self.can_undo():
            command = self.history[self.current_position]
            result = command.undo()
            self.current_position -= 1
            return result
        return None
    
    def redo(self) -> Any:
        if self.can_redo():
            self.current_position += 1
            command = self.history[self.current_position]
            return command.execute()
        return None
    
    def can_undo(self) -> bool:
        return self.current_position >= 0
    
    def can_redo(self) -> bool:
        return self.current_position < len(self.history) - 1
    
    def get_history(self) -> List[str]:
        return [f"{i}: {type(cmd).__name__}" for i, cmd in enumerate(self.history)]