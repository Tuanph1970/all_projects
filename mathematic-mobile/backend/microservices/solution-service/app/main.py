import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import httpx

from .services.ocr_service import OCRService
from .services.solver_service import MathSolverService
from .database import get_db_connection, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mathematics Solution Service",
    description="ML/AI Service for solving mathematical problems",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ocr_service = OCRService()
solver_service = MathSolverService()

# Request/Response Models
class ProcessImageRequest(BaseModel):
    problem_id: int
    image_path: str
    user_id: int

class SolveProblemRequest(BaseModel):
    problem_id: int
    problem_text: str
    category: Optional[str] = "General"
    user_id: int

class SolutionResponse(BaseModel):
    success: bool
    problem_id: int
    extracted_text: Optional[str] = None
    solution: Optional[str] = None
    steps: Optional[List[str]] = None
    confidence: Optional[float] = None
    message: str

class Solution(BaseModel):
    id: int
    problem_id: int
    user_id: int
    solution_text: str
    steps: Optional[str] = None
    method: str
    confidence: float
    processing_time_ms: int
    created_at: datetime

# Startup event
@app.on_event("startup")
async def startup():
    logger.info("Starting Solution Service...")
    init_db()
    logger.info("Solution Service started successfully")

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "solution-service",
        "timestamp": datetime.utcnow().isoformat()
    }

# Process image (OCR)
@app.post("/api/v1/solutions/process-image", response_model=SolutionResponse)
async def process_image(request: ProcessImageRequest, background_tasks: BackgroundTasks):
    """Extract text from uploaded image using OCR"""
    try:
        logger.info(f"Processing image for problem {request.problem_id}")

        # Get the actual file path
        upload_path = os.environ.get("UPLOAD_PATH", "/app/uploads")
        full_path = os.path.join(upload_path, request.image_path)

        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"Image not found: {request.image_path}")

        # Extract text using OCR
        extracted_text = await ocr_service.extract_text(full_path)

        if not extracted_text:
            return SolutionResponse(
                success=False,
                problem_id=request.problem_id,
                message="Could not extract text from image"
            )

        # Update problem status via Problem Service
        background_tasks.add_task(
            update_problem_status,
            request.problem_id,
            "Processing",
            extracted_text
        )

        return SolutionResponse(
            success=True,
            problem_id=request.problem_id,
            extracted_text=extracted_text,
            message="Text extracted successfully"
        )

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Solve problem
@app.post("/api/v1/solutions/solve", response_model=SolutionResponse)
async def solve_problem(request: SolveProblemRequest, background_tasks: BackgroundTasks):
    """Solve a mathematical problem"""
    try:
        logger.info(f"Solving problem {request.problem_id}: {request.problem_text[:50]}...")

        start_time = datetime.utcnow()

        # Solve the problem
        result = await solver_service.solve(
            problem_text=request.problem_text,
            category=request.category
        )

        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        if not result["success"]:
            return SolutionResponse(
                success=False,
                problem_id=request.problem_id,
                message=result.get("error", "Could not solve problem")
            )

        # Save solution to database
        solution_id = await save_solution(
            problem_id=request.problem_id,
            user_id=request.user_id,
            solution_text=result["solution"],
            steps=result.get("steps"),
            method=result.get("method", "symbolic"),
            confidence=result.get("confidence", 0.9),
            processing_time=processing_time
        )

        # Update problem status
        background_tasks.add_task(
            update_problem_status,
            request.problem_id,
            "Solved",
            None
        )

        return SolutionResponse(
            success=True,
            problem_id=request.problem_id,
            solution=result["solution"],
            steps=result.get("steps", []),
            confidence=result.get("confidence", 0.9),
            message="Problem solved successfully"
        )

    except Exception as e:
        logger.error(f"Error solving problem: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get solution by problem ID
@app.get("/api/v1/solutions/problem/{problem_id}")
async def get_solution_by_problem(problem_id: int):
    """Get solution for a specific problem"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM Solutions WHERE problem_id = %s ORDER BY created_at DESC LIMIT 1",
            (problem_id,)
        )
        solution = cursor.fetchone()

        cursor.close()
        conn.close()

        if not solution:
            raise HTTPException(status_code=404, detail="Solution not found")

        return {"success": True, "data": solution}

    except Exception as e:
        logger.error(f"Error getting solution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get solutions by user
@app.get("/api/v1/solutions/user/{user_id}")
async def get_user_solutions(user_id: int, page: int = 1, page_size: int = 10):
    """Get all solutions for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        offset = (page - 1) * page_size

        cursor.execute(
            """SELECT s.*, p.title as problem_title
               FROM Solutions s
               LEFT JOIN Problems p ON s.problem_id = p.id
               WHERE s.user_id = %s
               ORDER BY s.created_at DESC
               LIMIT %s OFFSET %s""",
            (user_id, page_size, offset)
        )
        solutions = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) as count FROM Solutions WHERE user_id = %s", (user_id,))
        total = cursor.fetchone()["count"]

        cursor.close()
        conn.close()

        return {
            "success": True,
            "data": {
                "solutions": solutions,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }

    except Exception as e:
        logger.error(f"Error getting user solutions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def save_solution(
    problem_id: int,
    user_id: int,
    solution_text: str,
    steps: List[str],
    method: str,
    confidence: float,
    processing_time: int
) -> int:
    """Save solution to database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    steps_json = str(steps) if steps else None

    cursor.execute(
        """INSERT INTO Solutions
           (problem_id, user_id, solution_text, steps, method, confidence, processing_time_ms, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
        (problem_id, user_id, solution_text, steps_json, method, confidence, processing_time)
    )

    solution_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return solution_id

async def update_problem_status(problem_id: int, status: str, extracted_text: Optional[str]):
    """Update problem status in Problem Service"""
    try:
        problem_service_url = os.environ.get("PROBLEM_SERVICE_URL", "http://problem-service:8002")
        internal_token = os.environ.get("INTERNAL_SERVICE_TOKEN", "internal-service-token")

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{problem_service_url}/api/v1/problems/{problem_id}/status",
                json={
                    "status": status,
                    "extracted_text": extracted_text
                },
                headers={"X-Service-Token": internal_token}
            )

            if response.status_code != 200:
                logger.warning(f"Failed to update problem status: {response.text}")

    except Exception as e:
        logger.error(f"Error updating problem status: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SERVICE_PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)
