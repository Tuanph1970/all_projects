from typing import List, Optional

from pydantic import BaseModel, Field


class ComparableListing(BaseModel):
    """
    One listing behind the aggregate.

    No seller field, on purpose -- see services/position.py::_sample.
    `product_id` is null for an external listing, which has no row here.
    """
    product_id: Optional[int] = None
    name: str
    price: float
    source: str = "mercai"   # mercai | external


class PricePoint(BaseModel):
    at: Optional[str] = None
    price: float
    reason: Optional[str] = None


class CategoryBenchmarkOut(BaseModel):
    """
    A whole-category aggregate from another marketplace.

    Reference material, not part of the seller's position: it is a different
    market with a different mix of products, and `caveat` says how.
    """
    source: str
    label: Optional[str] = None
    sample_size: int = 0
    catalogue_total: Optional[int] = None
    p25: Optional[float] = None
    median: Optional[float] = None
    p75: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    computed_at: Optional[str] = None
    stale: bool = False
    caveat: Optional[str] = None


class ObservationPoint(BaseModel):
    at: Optional[str] = None
    price: float
    confidence: Optional[int] = None
    trusted: bool = False
    stale: bool = False


class CompetitorSeries(BaseModel):
    """
    One tracked listing's readings over time.

    Points, not a line. These come from irregular seller-triggered fetches, so
    nothing is known about the gaps between them.
    """
    comparable_id: int
    source_host: str
    label: Optional[str] = None
    is_active: bool = True
    points: List[ObservationPoint] = Field(default_factory=list)


class UndercutAlert(BaseModel):
    type: str
    comparable_id: int
    source_host: str
    label: Optional[str] = None
    their_price: float
    your_price: float
    gap_percent: float
    observed_at: Optional[str] = None
    readings_agreeing: int
    # Plain about the fact that nothing watches continuously.
    evaluated: str


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
    # How many of the above came from seller-pasted URLs.
    external_count: int = 0
    min_comparable_n: int

    p25: Optional[float] = None
    median: Optional[float] = None
    p75: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None

    comparables: List[ComparableListing] = Field(default_factory=list)
    # Exact, from the price_history ledger -- safe to draw as a real line.
    trend: List[PricePoint] = Field(default_factory=list)
    # Wider market reference. Never folded into the statistics above.
    benchmark: Optional[CategoryBenchmarkOut] = None
    competitor_series: List[CompetitorSeries] = Field(default_factory=list)
    alerts: List[UndercutAlert] = Field(default_factory=list)
