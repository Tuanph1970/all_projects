"""
Bulk price updates must write history too (PR 2).

This path is the reason PR 2 needed restructuring: it previously used
`Query.update()`, which issues raw SQL without loading the objects, so the old
price was never in memory and could not be recorded.
"""
from decimal import Decimal

from shared.models.product import PriceHistory, Product


def history(db, product_id=None):
    query = db.query(PriceHistory)
    if product_id is not None:
        query = query.filter(PriceHistory.product_id == product_id)
    return query.order_by(PriceHistory.id).all()


def test_bulk_update_records_every_change(client, db, products):
    bowl, plate = products

    response = client.post(
        "/api/v1/seller/bulk-operations/update-prices",
        json=[
            {"product_id": bowl.id, "price": 24.00},
            {"product_id": plate.id, "price": 18.50},
        ],
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Updated prices for 2 products"

    rows = history(db)
    assert len(rows) == 2
    assert {r.change_reason for r in rows} == {"bulk_update"}

    by_product = {r.product_id: r for r in rows}
    assert by_product[bowl.id].old_price == Decimal("20.00")
    assert by_product[bowl.id].new_price == Decimal("24.00")
    assert by_product[plate.id].old_price == Decimal("15.00")
    assert by_product[plate.id].new_price == Decimal("18.50")


def test_bulk_update_actually_changes_the_price(client, db, products):
    """The restructure swapped Query.update() for ORM assignment -- verify the
    prices still land, not just the history rows."""
    bowl = products[0]

    client.post(
        "/api/v1/seller/bulk-operations/update-prices",
        json=[{"product_id": bowl.id, "price": 24.00}],
    )

    db.expire_all()
    assert db.query(Product).filter(Product.id == bowl.id).one().price == Decimal("24.00")


def test_unchanged_price_writes_no_row(client, db, products):
    """Re-submitting the current price is a no-op, not a phantom change."""
    bowl = products[0]

    response = client.post(
        "/api/v1/seller/bulk-operations/update-prices",
        json=[{"product_id": bowl.id, "price": 20.00}],
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Updated prices for 0 products"
    assert history(db) == []


def test_ledger_matches_products_after_bulk_update(client, db, products):
    """The drift check from the plan, in miniature: ledger vs reality."""
    bowl, plate = products

    client.post(
        "/api/v1/seller/bulk-operations/update-prices",
        json=[
            {"product_id": bowl.id, "price": 24.00},
            {"product_id": plate.id, "price": 18.50},
        ],
    )

    db.expire_all()
    for product in db.query(Product).all():
        rows = history(db, product.id)
        assert rows, f"product {product.id} has no history"
        assert product.price == rows[-1].new_price


def test_cannot_bulk_update_another_sellers_product(client, db, products, other_seller):
    """Tenant isolation must survive the restructure."""
    from shared.models.product import Product as P

    rival_product = P(name="Rival vase", description="theirs", price=99,
                      quantity_available=1, seller_id=other_seller.id, is_active=True)
    db.add(rival_product)
    db.commit()
    db.refresh(rival_product)

    response = client.post(
        "/api/v1/seller/bulk-operations/update-prices",
        json=[{"product_id": rival_product.id, "price": 1.00}],
    )

    assert response.status_code == 404
    db.expire_all()
    assert db.query(P).filter(P.id == rival_product.id).one().price == Decimal("99.00")
    assert history(db, rival_product.id) == []
