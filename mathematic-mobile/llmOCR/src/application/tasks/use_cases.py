"""
Task application use cases.

GetTaskUseCase: look up a task by ID and return its current state.
"""
from ...domain.shared.value_objects import MLTask
from ...domain.shared.exceptions import TaskNotFoundError
from ...domain.tasks.repositories import ITaskRepository


class GetTaskUseCase:
    """Return the current state of an async processing task."""

    def __init__(self, task_repo: ITaskRepository) -> None:
        self._repo = task_repo

    def execute(self, task_id: str) -> MLTask:
        task = self._repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task


class ListTasksUseCase:
    """Return all tasks (newest first) — useful for monitoring / debugging."""

    def __init__(self, task_repo: ITaskRepository) -> None:
        self._repo = task_repo

    def execute(self) -> list:
        return self._repo.list_all()
