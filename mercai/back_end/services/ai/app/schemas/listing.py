from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DraftListing(BaseModel):
    """
    An unsaved listing, straight from the create form.

    The highest-value moment for the optimizer is the seller's first draft,
    before anything is saved -- so the API must not require a product row.
    """
    name: str
    description: str
    tags: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    technique: Optional[str] = None
    dimensions: Optional[str] = None
    category_id: Optional[int] = None


class ListingSuggestRequest(BaseModel):
    # Exactly one of these. `product_id` for a saved listing, `draft` for one
    # still being typed.
    product_id: Optional[int] = None
    draft: Optional[DraftListing] = None
    # Optional narrowing; defaults to every field the optimizer supports.
    fields: Optional[List[str]] = None


class ListingSuggestResponse(BaseModel):
    suggestion_id: int
    product_id: Optional[int] = None
    model: str
    prompt_version: str
    cached: bool = False
    latency_ms: Optional[int] = None
    suggestions: Dict[str, Any] = Field(default_factory=dict)
    image_report: Dict[str, Any] = Field(default_factory=dict)


class ResolveRequest(BaseModel):
    status: str  # accepted | partially_accepted | rejected
    accepted_fields: Optional[List[str]] = None


class ResolveResponse(BaseModel):
    suggestion_id: int
    status: str
    resolved_at: Optional[str] = None
