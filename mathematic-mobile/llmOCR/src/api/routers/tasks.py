"""
Tasks router — thin HTTP adapter for async task polling.

Endpoints:
  GET  /tasks/{task_id}   — poll a single task
  GET  /tasks/            — list all tasks (admin)
  DELETE /tasks/{task_id} — cancel / remove a task record
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ...application.tasks.use_cases import GetTaskUseCase, ListTasksUseCase
from ...api.dependencies import get_get_task_use_case, get_list_tasks_use_case
from ...domain.shared.exceptions import TaskNotFoundError

router = APIRouter()


# ── Response schemas ──────────────────────────────────────────────────────────

class TaskResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{task_id}", response_model=TaskResponse, summary="Poll a task")
async def get_task(
    task_id: str,
    use_case: GetTaskUseCase = Depends(get_get_task_use_case),
):
    """
    Return the current status and result of an async task.

    - **pending** — queued, not started yet
    - **processing** — currently running
    - **completed** — finished; `result` contains the output
    - **failed** — an error occurred; `error_message` has details
    """
    try:
        task = use_case.execute(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    result_payload: Optional[Dict[str, Any]] = None
    if task.result is not None:
        # Pydantic model → plain dict for JSON serialisation
        result_payload = task.result.model_dump() if hasattr(task.result, "model_dump") else vars(task.result)

    return TaskResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status.value,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
        result=result_payload,
        error_message=task.error_message,
    )


@router.get("/", response_model=List[TaskResponse], summary="List all tasks")
async def list_tasks(
    use_case: ListTasksUseCase = Depends(get_list_tasks_use_case),
):
    """Return all tasks ordered by creation time (newest first)."""
    tasks = use_case.execute()
    return [
        TaskResponse(
            task_id=t.id,
            task_type=t.task_type,
            status=t.status.value,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
            result=(t.result.model_dump() if t.result and hasattr(t.result, "model_dump") else None),
            error_message=t.error_message,
        )
        for t in tasks
    ]


@router.delete("/{task_id}", summary="Delete a task record")
async def delete_task(task_id: str, request: Request):
    """Remove a task record from the store."""
    repo = request.app.state.task_repository
    deleted = repo.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"deleted": True, "task_id": task_id}
