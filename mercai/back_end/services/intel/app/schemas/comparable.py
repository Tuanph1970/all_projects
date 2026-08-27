from typing import List, Optional

from pydantic import BaseModel, Field


class AddComparableRequest(BaseModel):
    product_id: int
    url: str
    label: Optional[str] = None


class ObservationOut(BaseModel):
    observed_at: Optional[str] = None
    status: str
    # Plain language for the seller. The status taxonomy is the contract; this
    # is the sentence that goes on screen.
    message: str
    price: Optional[float] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    is_range: bool = False
    currency: Optional[str] = None
    availability: Optional[str] = None
    confidence: Optional[int] = None
    extractor_tier: Optional[str] = None
    # True when this reading is good enough to move the market statistics.
    trusted: bool = False
    stale: bool = False


class ComparableOut(BaseModel):
    id: int
    product_id: int
    url: str
    source_host: str
    label: Optional[str] = None
    is_active: bool
    consecutive_failures: int = 0
    last_fetched_at: Optional[str] = None
    latest: Optional[ObservationOut] = None


class ComparableListResponse(BaseModel):
    product_id: int
    comparables: List[ComparableOut] = Field(default_factory=list)
    supported_hosts: List[str] = Field(default_factory=list)
