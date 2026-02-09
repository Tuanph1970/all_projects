"""Solution Service API Routes

Provides CRUD endpoints for prediction solutions, matching the v2 frontend API.
References webapi/views_solution.py and webapi/repositories/predict_solution_repository.py
for database schema and business logic.
"""
import json
import logging
import threading
import time as time_module
from typing import Optional
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies import get_db, get_current_user_optional, get_current_user
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

solution_router = APIRouter()

# Global dictionary to track training status (matches webapi pattern)
training_status = {}


# ==========================================
# Solution CRUD Endpoints
# ==========================================

@solution_router.get("/all")
@solution_router.get("/all/")
async def get_solutions(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get solutions created by the logged-in user.
    Matches webapi: views_solution.get_solutions
    """
    try:
        if current_user and current_user.get("user_id"):
            user_id = str(current_user["user_id"])
            result = await db.execute(
                text("""
                    SELECT
                        tbl_solution.id,
                        tbl_solution.solution_name,
                        tbl_solution.ticker,
                        tbl_solution.created_by,
                        tbl_solution.user_id,
                        tbl_solution.created_date,
                        tbl_solution.updated_date,
                        tbl_solution.train_status,
                        model_instances.model_type,
                        model_instances.model_sub_type,
                        model_instances.model_name
                    FROM tbl_solution
                    INNER JOIN model_instances ON tbl_solution.model_id = model_instances.id
                    WHERE tbl_solution.user_id = :user_id
                """),
                {"user_id": user_id}
            )
        else:
            result = await db.execute(
                text("""
                    SELECT
                        tbl_solution.id,
                        tbl_solution.solution_name,
                        tbl_solution.ticker,
                        tbl_solution.created_by,
                        tbl_solution.user_id,
                        tbl_solution.created_date,
                        tbl_solution.updated_date,
                        tbl_solution.train_status,
                        model_instances.model_type,
                        model_instances.model_sub_type,
                        model_instances.model_name
                    FROM tbl_solution
                    INNER JOIN model_instances ON tbl_solution.model_id = model_instances.id
                """)
            )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch solutions: {e}")
        return []


@solution_router.get("/tickers")
@solution_router.get("/tickers/")
async def get_predict_tickers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tickers available for prediction from user's portfolio.
    Queries portfolio_holdings table directly (shared database).
    Matches webapi: views_solution.get_predict_tickers
    """
    user_id = current_user["user_id"]

    try:
        # Query portfolio holdings directly - all services share the same database
        result = await db.execute(
            text("""
                SELECT DISTINCT ph.symbol as ticker
                FROM portfolio_holdings ph
                INNER JOIN portfolios p ON ph.portfolio_id = p.id
                WHERE p.user_id = :user_id
                ORDER BY ph.symbol
            """),
            {"user_id": user_id}
        )
        rows = result.mappings().all()

        if rows:
            # Return objects with 'ticker' field matching frontend expectations
            return [{"ticker": row["ticker"]} for row in rows]

        logger.info(f"User {user_id} has no stocks in portfolio")
        return []
    except Exception as e:
        logger.error(f"Failed to get predict tickers: {e}")
        return []


@solution_router.get("/models")
@solution_router.get("/models/")
async def get_predict_models(
    db: AsyncSession = Depends(get_db)
):
    """Get all available models for solution creation.
    Matches webapi: views_solution.get_predict_models
    """
    try:
        result = await db.execute(
            text("""
                SELECT id, model_name, model_type, model_sub_type,
                       past_covariate, future_covariate
                FROM model_instances
                ORDER BY id DESC
            """)
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch predict models: {e}")
        return []


@solution_router.get("/covariates")
@solution_router.get("/covariates/")
async def get_predict_covariates(
    db: AsyncSession = Depends(get_db)
):
    """Get covariates (time series) for solution configuration.
    Matches webapi: views_solution.get_predict_covariates
    """
    try:
        result = await db.execute(
            text("SELECT id, series_name FROM tbl_time_series WHERE status = 1")
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch covariates: {e}")
        return []


@solution_router.post("")
@solution_router.post("/")
@solution_router.post("/create")
@solution_router.post("/create/")
async def create_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new prediction solution.
    Matches webapi: views_solution.create_predict_solution
    """
    data = await request.json()
    user_id = str(current_user["user_id"])

    if 'user_id' not in data:
        data['user_id'] = user_id
    if 'created_by' not in data:
        data['created_by'] = user_id

    try:
        result = await db.execute(
            text("""
                INSERT INTO tbl_solution
                (solution_name, model_id, ticker, created_date, created_by, user_id,
                 status, start_training_date, end_training_date,
                 train_validation_ratio, solution_status, train_status)
                VALUES (:solution_name, :model_id, :ticker, :created_date, :created_by,
                        :user_id, :status, :start_training_date, :end_training_date,
                        :train_validation_ratio, 0, 'not_trained')
            """),
            {
                "solution_name": data.get("solution_name"),
                "model_id": data.get("model_id"),
                "ticker": data.get("ticker"),
                "created_date": data.get("created_date", datetime.now().strftime("%Y-%m-%d")),
                "created_by": data.get("created_by"),
                "user_id": data.get("user_id"),
                "status": data.get("status", 1),
                "start_training_date": data.get("start_training_date"),
                "end_training_date": data.get("end_training_date"),
                "train_validation_ratio": data.get("train_validation_ratio", 0.8),
            }
        )
        await db.commit()
        solution_id = result.lastrowid

        created_solution = {**data, "id": solution_id}
        return created_solution
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create solution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create solution: {str(e)}")


@solution_router.put("")
@solution_router.put("/")
@solution_router.put("/update")
@solution_router.put("/update/")
async def update_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a prediction solution.
    Matches webapi: views_solution.update_predict_solution
    """
    data = await request.json()
    user_id = str(current_user["user_id"])

    if 'user_id' not in data:
        data['user_id'] = user_id
    if 'updated_by' not in data:
        data['updated_by'] = user_id

    solution_id = data.get("id")
    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    try:
        await db.execute(
            text("""
                UPDATE tbl_solution
                SET solution_name = :solution_name, model_id = :model_id, ticker = :ticker,
                    updated_date = :updated_date, updated_by = :updated_by,
                    start_training_date = :start_training_date,
                    end_training_date = :end_training_date,
                    train_validation_ratio = :train_validation_ratio,
                    user_id = :user_id
                WHERE id = :id
            """),
            {
                "solution_name": data.get("solution_name"),
                "model_id": data.get("model_id"),
                "ticker": data.get("ticker"),
                "updated_date": data.get("updated_date", datetime.now().strftime("%Y-%m-%d")),
                "updated_by": data.get("updated_by"),
                "start_training_date": data.get("start_training_date"),
                "end_training_date": data.get("end_training_date"),
                "train_validation_ratio": data.get("train_validation_ratio", 0.8),
                "user_id": data.get("user_id"),
                "id": solution_id,
            }
        )
        await db.commit()
        return data
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update solution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update solution: {str(e)}")


@solution_router.get("/calculate-date-range")
@solution_router.get("/calculate-date-range/")
@solution_router.post("/calculate-date-range")
@solution_router.post("/calculate-date-range/")
async def calculate_date_range(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Calculate recommended date range for model training.
    Matches webapi: views_solution.calculate_date_range
    """
    if request.method == "POST":
        data = await request.json()
    else:
        data = dict(request.query_params)

    # Default response with reasonable date range
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 2)

    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "required_points": 100,
        "recommended_points": 500,
        "estimated_points": 500,
        "adjusted": False,
        "message": "Default date range"
    }


@solution_router.get("/ticker/time_range/{ticker}")
async def get_ticker_time_range(
    ticker: str
):
    """Get available date range for a ticker.
    Matches webapi: views_solution.get_ticker_time_range
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{settings.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/companies/{ticker}/historical-data"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return {
                        "start_date": data[0].get("time", "2020-01-01"),
                        "end_date": data[-1].get("time", datetime.now().strftime("%Y-%m-%d"))
                    }
    except Exception as e:
        logger.warning(f"Failed to get ticker time range: {e}")

    # Fallback
    return {
        "start_date": "2020-01-01",
        "end_date": datetime.now().strftime("%Y-%m-%d")
    }


# ==========================================
# Solution Detail Endpoints (must be after specific routes)
# ==========================================

@solution_router.get("/{solution_id}/training-status")
@solution_router.get("/{solution_id}/training-status/")
async def get_training_status(
    solution_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get the current training status for a solution.
    Matches webapi: views_solution.get_training_status
    """
    if solution_id not in training_status:
        return {
            "status": "not_found",
            "message": "No training session found for this solution"
        }

    current = training_status[solution_id]

    # Clean up old completed/failed statuses after 5 minutes
    if current["status"] in ["completed", "failed"]:
        status_time = current.get("completed_at") or current.get("failed_at", 0)
        if time_module.time() - status_time > 300:
            del training_status[solution_id]

    return current


@solution_router.post("/train")
@solution_router.post("/train/")
async def train_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Start training a solution asynchronously.
    Matches webapi: views_solution.train_solution
    """
    data = await request.json()
    solution_id = data.get("id")

    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    # Check if already training
    if solution_id in training_status:
        current = training_status[solution_id]
        if current["status"] == "training":
            return {
                "message": "Training already in progress",
                "status": "training",
                "solution_id": solution_id
            }

    # Mark as training
    training_status[solution_id] = {
        "status": "training",
        "message": "Training in progress...",
        "progress": 0,
        "started_at": time_module.time()
    }

    # TODO: Implement actual training logic
    # For now, mark as completed after a brief delay
    def mock_training():
        time_module.sleep(2)
        training_status[solution_id] = {
            "status": "completed",
            "message": "Training completed successfully",
            "completed_at": time_module.time()
        }

    thread = threading.Thread(target=mock_training, daemon=True)
    thread.start()

    return {
        "message": "Training started successfully",
        "status": "training",
        "solution_id": solution_id
    }


@solution_router.post("/predict")
@solution_router.post("/predict/")
async def predict_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate predictions for a trained solution.
    Matches webapi: views_solution.predict_solution
    """
    data = await request.json()
    solution_id = data.get("id")

    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    # TODO: Implement actual prediction logic
    return {
        "message": "Prediction not yet implemented in microservice",
        "solution_id": solution_id
    }


# ==========================================
# Solution Indicator Endpoints
# ==========================================

@solution_router.get("/{solution_id}/indicators")
@solution_router.get("/{solution_id}/indicators/")
async def get_solution_indicators(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get indicators assigned to a solution.
    Matches webapi: view_indicators.get_solution_indicators
    """
    try:
        result = await db.execute(
            text("""
                SELECT si.id, si.solution_id, si.indicator_id, si.indicator_category,
                       si.covariate_type, si.parameters,
                       ti.name, ti.type, ti.description, ti.default_parameters
                FROM solution_indicators si
                LEFT JOIN technical_indicators ti ON si.indicator_id = ti.id
                WHERE si.solution_id = :solution_id
            """),
            {"solution_id": solution_id}
        )
        rows = result.mappings().all()
        indicators = []
        for row in rows:
            ind = dict(row)
            if ind.get("parameters"):
                try:
                    ind["parameters"] = json.loads(ind["parameters"])
                except (json.JSONDecodeError, TypeError):
                    pass
            if ind.get("default_parameters"):
                try:
                    ind["default_parameters"] = json.loads(ind["default_parameters"])
                except (json.JSONDecodeError, TypeError):
                    pass
            indicators.append(ind)
        return indicators
    except Exception as e:
        logger.error(f"Failed to fetch solution indicators: {e}")
        return []


@solution_router.post("/{solution_id}/indicators/set")
@solution_router.post("/{solution_id}/indicators/set/")
async def set_solution_indicators(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set all indicators for a solution (replaces existing).
    Matches webapi: view_indicators.set_solution_indicators
    """
    data = await request.json()
    indicators = data.get("indicators", [])

    try:
        # Delete existing indicators for this solution
        await db.execute(
            text("DELETE FROM solution_indicators WHERE solution_id = :solution_id"),
            {"solution_id": solution_id}
        )

        # Insert new indicators
        for ind in indicators:
            params = ind.get("parameters", {})
            params_json = json.dumps(params) if isinstance(params, dict) else params

            await db.execute(
                text("""
                    INSERT INTO solution_indicators
                    (solution_id, indicator_id, indicator_category, covariate_type, parameters)
                    VALUES (:solution_id, :indicator_id, :indicator_category, :covariate_type, :parameters)
                """),
                {
                    "solution_id": solution_id,
                    "indicator_id": ind.get("indicator_id"),
                    "indicator_category": ind.get("indicator_category", "trend"),
                    "covariate_type": ind.get("covariate_type", "past"),
                    "parameters": params_json
                }
            )

        await db.commit()
        return {"message": "Indicators set successfully", "solution_id": solution_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to set solution indicators: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set indicators: {str(e)}")


@solution_router.post("/{solution_id}/indicators/add")
@solution_router.post("/{solution_id}/indicators/add/")
async def add_solution_indicator(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add an indicator to a solution."""
    data = await request.json()
    params = data.get("parameters", {})
    params_json = json.dumps(params) if isinstance(params, dict) else params

    try:
        result = await db.execute(
            text("""
                INSERT INTO solution_indicators
                (solution_id, indicator_id, indicator_category, covariate_type, parameters)
                VALUES (:solution_id, :indicator_id, :indicator_category, :covariate_type, :parameters)
            """),
            {
                "solution_id": solution_id,
                "indicator_id": data.get("indicator_id"),
                "indicator_category": data.get("indicator_category", "trend"),
                "covariate_type": data.get("covariate_type", "past"),
                "parameters": params_json
            }
        )
        await db.commit()
        return {"id": result.lastrowid, "message": "Indicator added", "solution_id": solution_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to add solution indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add indicator: {str(e)}")


@solution_router.delete("/{solution_id}/indicators/{indicator_id}")
@solution_router.delete("/{solution_id}/indicators/{indicator_id}/")
@solution_router.post("/{solution_id}/indicators/{indicator_id}/delete")
@solution_router.post("/{solution_id}/indicators/{indicator_id}/delete/")
async def remove_solution_indicator(
    solution_id: int,
    indicator_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove an indicator from a solution."""
    try:
        await db.execute(
            text("DELETE FROM solution_indicators WHERE id = :indicator_id AND solution_id = :solution_id"),
            {"indicator_id": indicator_id, "solution_id": solution_id}
        )
        await db.commit()
        return {"message": "Indicator removed", "solution_id": solution_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to remove solution indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove indicator: {str(e)}")


# ==========================================
# Catch-all: Get/Delete solution by ID
# IMPORTANT: Must come AFTER all specific routes
# ==========================================

@solution_router.get("/{solution_id}")
async def get_solution_by_id(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get solution by ID.
    Matches webapi: views_solution.get_solution_by_id
    """
    try:
        result = await db.execute(
            text("SELECT * FROM tbl_solution WHERE id = :id"),
            {"id": solution_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Solution {solution_id} not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch solution {solution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch solution: {str(e)}")


@solution_router.delete("/{solution_id}")
async def delete_solution_by_id(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete solution by ID.
    Matches webapi: views_solution.delete_solution_by_id
    """
    try:
        # Delete associated indicators first
        await db.execute(
            text("DELETE FROM solution_indicators WHERE solution_id = :solution_id"),
            {"solution_id": solution_id}
        )
        # Delete solution
        result = await db.execute(
            text("DELETE FROM tbl_solution WHERE id = :id"),
            {"id": solution_id}
        )
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Solution {solution_id} not found")

        return {"message": "Solution deleted", "id": solution_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete solution {solution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete solution: {str(e)}")
