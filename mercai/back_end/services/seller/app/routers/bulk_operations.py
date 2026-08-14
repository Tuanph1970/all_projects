# Bulk Operations Router for Seller Service
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy.orm import Session
from typing import List, Any
from pydantic import BaseModel
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from shared.database import get_db
from shared.models.user import User
from shared.models.product import Product
from shared.security import get_current_user

router = APIRouter()


from typing import Union

class BulkStatusUpdate(BaseModel):
    product_ids: List[Union[int, str]]
    is_active: bool

    class Config:
        # Allow string to int coercion
        coerce_numbers_to_str = False


class BulkStatusResponse(BaseModel):
    updated_count: int
    message: str


# Debug endpoint to see raw request
@router.post("/bulk-operations/debug")
async def debug_bulk_request(request: Request):
    body = await request.body()
    print(f"[DEBUG] Raw body: {body}")
    try:
        json_body = await request.json()
        print(f"[DEBUG] JSON body: {json_body}")
        return {"received": json_body}
    except Exception as e:
        return {"error": str(e), "raw": body.decode()}


@router.post("/bulk-operations/update-status")
def bulk_update_product_status(
    update_request: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk update product status (activate/deactivate) for the current seller.
    Only updates products owned by the authenticated seller.
    """
    print(f"[DEBUG] Received raw request: {update_request}")
    print(f"[DEBUG] Request type: {type(update_request)}")
    print(f"[DEBUG] Current user: {current_user.id if current_user else 'None'}")

    # Extract from dict
    raw_product_ids = update_request.get('product_ids', [])
    is_active = update_request.get('is_active', True)

    print(f"[DEBUG] Raw product_ids: {raw_product_ids}, type: {type(raw_product_ids)}")
    print(f"[DEBUG] is_active: {is_active}")

    # Convert product_ids to integers
    product_ids = [int(pid) for pid in raw_product_ids]
    print(f"[DEBUG] Product IDs (converted): {product_ids}")

    # Get products owned by current seller
    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.seller_id == current_user.id
    ).all()

    if not products:
        raise HTTPException(
            status_code=404,
            detail="No products found matching the provided IDs for this seller"
        )

    # Update status for all matching products
    updated_count = 0
    for product in products:
        product.is_active = is_active
        updated_count += 1

    db.commit()

    status_text = "activated" if is_active else "deactivated"
    return {
        "updated_count": updated_count,
        "message": f"Successfully {status_text} {updated_count} product(s)"
    }
