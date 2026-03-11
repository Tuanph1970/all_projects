"""
Domain-level exceptions.

These live in the domain layer so application use cases can raise them
without importing from the API layer (which would be a layering violation).
The API layer catches these and converts them to HTTP responses.
"""


class DomainException(Exception):
    """Base for all domain-level exceptions."""


class ModelUnavailableError(DomainException):
    """Raised by a use case when a required ML model is not registered or loaded."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        super().__init__(f"Model '{model_id}' is not available")


class TaskNotFoundError(DomainException):
    """Raised when a task ID cannot be found in the task repository."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"Task '{task_id}' not found")
