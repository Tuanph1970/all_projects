"""
Task repository interface (port).

Infrastructure adapters (in-memory, Redis) implement this.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from ..shared.value_objects import MLTask


class ITaskRepository(ABC):
    """Port for persisting and retrieving async processing tasks."""

    @abstractmethod
    def save(self, task: MLTask) -> None:
        """Insert or update a task record."""
        ...

    @abstractmethod
    def get(self, task_id: str) -> Optional[MLTask]:
        """Return the task with the given ID, or None if not found."""
        ...

    @abstractmethod
    def list_all(self) -> List[MLTask]:
        """Return all stored tasks (newest first)."""
        ...

    @abstractmethod
    def delete(self, task_id: str) -> bool:
        """Delete a task by ID. Returns True if it existed."""
        ...
