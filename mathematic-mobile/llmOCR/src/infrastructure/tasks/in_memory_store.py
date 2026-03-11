"""
In-memory task repository.

Stores tasks in a plain dict keyed by task_id.  Suitable for single-process
deployments and development.  Replace with a Redis adapter (P4) for
multi-worker or persistent deployments.
"""
from typing import Dict, List, Optional

from ...domain.shared.value_objects import MLTask
from ...domain.tasks.repositories import ITaskRepository


class InMemoryTaskRepository(ITaskRepository):
    """Thread-safe (GIL-protected) in-memory task store."""

    def __init__(self) -> None:
        self._store: Dict[str, MLTask] = {}

    def save(self, task: MLTask) -> None:
        self._store[task.id] = task

    def get(self, task_id: str) -> Optional[MLTask]:
        return self._store.get(task_id)

    def list_all(self) -> List[MLTask]:
        return sorted(self._store.values(), key=lambda t: t.created_at, reverse=True)

    def delete(self, task_id: str) -> bool:
        if task_id in self._store:
            del self._store[task_id]
            return True
        return False

    def __len__(self) -> int:
        return len(self._store)
