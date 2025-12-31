class StockApiException(Exception):
    pass


class EntityNotFoundException(StockApiException):
    def __init__(self, entity_type: str, identifier: str):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} with identifier '{identifier}' not found")


class ValidationException(StockApiException):
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)


class DatabaseException(StockApiException):
    def __init__(self, message: str, original_exception: Exception = None):
        self.original_exception = original_exception
        super().__init__(message)


class ExternalServiceException(StockApiException):
    def __init__(self, service_name: str, message: str):
        self.service_name = service_name
        super().__init__(f"External service '{service_name}' error: {message}")


class ModelCreationException(StockApiException):
    def __init__(self, model_type: str, message: str):
        self.model_type = model_type
        super().__init__(f"Failed to create {model_type} model: {message}")


class AgentExecutionException(StockApiException):
    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        super().__init__(f"Agent '{agent_name}' execution failed: {message}")


class IndicatorValidationException(StockApiException):
    """Exception for indicator validation failures with user-friendly suggestions"""
    def __init__(self, indicator_name: str, indicator_type: str, message: str, suggestions: list = None):
        self.indicator_name = indicator_name
        self.indicator_type = indicator_type
        self.suggestions = suggestions or []
        super().__init__(message)


class SolutionTrainingException(StockApiException):
    def __init__(self, solution_id: str, message: str, suggestions: list = None):
        self.solution_id = solution_id
        self.suggestions = suggestions or []
        super().__init__(f"Solution '{solution_id}' training failed: {message}")


class TimeSeriesException(StockApiException):
    def __init__(self, message: str):
        super().__init__(f"Time series operation failed: {message}")


class StorageException(StockApiException):
    def __init__(self, message: str, original_exception: Exception = None):
        self.original_exception = original_exception
        super().__init__(f"Storage operation failed: {message}")


class PredictionException(StockApiException):
    def __init__(self, model_type: str, message: str):
        self.model_type = model_type
        super().__init__(f"Prediction error in {model_type} model: {message}")


class SimulationException(StockApiException):
    def __init__(self, message: str):
        super().__init__(f"Simulation error: {message}")