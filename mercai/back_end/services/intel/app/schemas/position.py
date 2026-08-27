from typing import List, Optional

from pydantic import BaseModel, Field


class ComparableListing(BaseModel):
    """
    One listing behind the aggregate.

    No seller field, on purpose -- see services/position.py::_sample.
    """
    product_id: int
    name: str
    price: float


class PricePoint(BaseModel):
    at: Optional[str] = None
    price: float
    reason: Optional[str] = None


class PricePositionResponse(BaseModel):
    product_id: int
    product_name: str
    own_price: float
    currency: str = "VND"

    # own_category | parent_category | none
    basis: str
    # The category the comparison was drawn from, for the client's copy. None
    # when there is no market view.
    basis_label: Optional[str] = None
    # below_market | in_range | above_market, or None with no market view.
    position: Optional[str] = None

    comparable_count: int = 0
    min_comparable_n: int

    p25: Optional[float] = None
    median: Optional[float] = None
    p75: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None

    comparables: List[ComparableListing] = Field(default_factory=list)
    # Exact, from the price_history ledger -- safe to draw as a real line.
    trend: List[PricePoint] = Field(default_factory=list)
