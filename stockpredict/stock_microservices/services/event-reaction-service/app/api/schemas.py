"""Pydantic request/response schemas for the Event-Reaction API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    event_id: str
    ts_utc: datetime  # tz-aware UTC (EC6)
    kind: str
    actual: float
    consensus: Optional[float] = None
    asset_scope: Optional[str] = None


class IngestRequest(BaseModel):
    events: list[EventIn]


class IngestResponse(BaseModel):
    ingested: int


class MeasureRequest(BaseModel):
    symbol: str
    market_symbol: str
    event: EventIn
    method: str = "consensus"
    jump_n_null: int = 0


class SurpriseOut(BaseModel):
    method: str
    s_raw: float
    s: float
    expected: float
    scale: float
    sign: int


class AbnormalOut(BaseModel):
    car: float
    alpha: float
    beta: float
    sigma_ar: float


class JumpOut(BaseModel):
    statistic: float
    threshold: float
    is_jump: bool
    sigma_local: float
    null_fpr: Optional[float] = None  # None when the null was not requested (jump_n_null=0)


class MeasureResponse(BaseModel):
    t0_index: int
    coverage: str
    surprise: SurpriseOut
    abnormal: AbnormalOut
    jump: JumpOut


class CrossSectionRow(BaseModel):
    asset: str
    event_date: datetime
    surprise: float
    car: float


class CrossSectionRequest(BaseModel):
    rows: list[CrossSectionRow]
    cluster: str = "event_date"


class CrossSectionResponse(BaseModel):
    gamma0: float
    gamma1: float
    se_gamma1: float
    cluster: str
    n_assets: int
    n_event_dates: int
    r_squared: float
