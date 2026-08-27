#!/usr/bin/env python3
"""
Seed a catalogue that price intelligence can actually be developed against.

WHY THIS EXISTS
    Checked 2026-08-27, the deployed database held one user and zero products.
    Phase 1 computes quartiles over `products`, so against an empty table every
    seller sees the "no market view" state -- and a correct implementation is
    indistinguishable from a broken one. This is the fixture that makes the
    difference visible.

WHAT IT BUILDS, AND WHY THIS SHAPE
    Two contrasting category trees, because Mercai is deliberately no longer
    ceramics-only and the two halves need different matchers:

      Gốm sứ  (artisan)     -- no model numbers anywhere in the titles, so
                               comparables can only ever be seller-declared
      Âm thanh (electronics) -- real manufacturer model codes, so listings
                               join exactly on a shared token

    Deliberate properties, each one exercising a rule in the design doc:

      * Bát đĩa      8 products / 3 sellers  -> quartiles are meaningful
      * Ấm chén      3 products / 3 sellers  -> BELOW MIN_COMPARABLE_N, so the
                                                parent-category fallback (§8.3
                                                rung 3) has something to fall
                                                back to
      * Ampli        7 products / 3 sellers  -> model tokens across sellers
      * Loa          6 products / 2 sellers
      * one seller's product is priced far above its category  -> the "above
        market" label has a case
      * one is far below                                       -> "below market"
      * price_history carries an origin row per product plus real changes on a
        few, so the trend line is not empty on day one

IDEMPOTENT
    Keyed on username / category name / sku. Re-running updates prices and adds
    nothing twice, so it is safe to leave in a bootstrap script.

USAGE
    docker exec mercai_intel_service python /app/scripts/seed_catalogue.py
    docker exec mercai_intel_service python /app/scripts/seed_catalogue.py --reset
    docker exec mercai_intel_service python /app/scripts/seed_catalogue.py --report-only

    (./scripts is mounted into the container by docker-compose. Running it on
    the host works too, but only if DB_HOST/DB_PORT point at the published
    MySQL port -- inside the container they are already right.)
"""
import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging  # noqa: E402

from shared.database import SessionLocal, engine, Base  # noqa: E402

# shared.database builds the engine at import time with echo=settings.DEBUG,
# and SQLAlchemy sets the logger level itself when echo is on -- so this has to
# come AFTER the import or it is silently overridden. This is an operator-facing
# tool; statement logs bury its report.
engine.echo = False
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
import shared.models  # noqa: F401,E402  - registers every model
from shared.models.user import User, UserRole  # noqa: E402
from shared.models.product import Category, Product, PriceHistory  # noqa: E402
from shared.security import get_password_hash  # noqa: E402

SEED_PASSWORD = "MercaiTest@2026"
SKU_PREFIX = "SEED-"

# --------------------------------------------------------------------------
# Sellers. `gomthuha` already exists on the dev box; keyed on username so the
# script adopts it rather than colliding with it.
# --------------------------------------------------------------------------
SELLERS = [
    ("gomthuha",    "seller.test@example.com", "Gốm Thu Hà",      "Gốm Thu Hà"),
    ("batrangvn",   "batrang@example.com",     "Trần Văn Bát",    "Bát Tràng Việt"),
    ("gomviet",     "gomviet@example.com",     "Lê Thị Gốm",      "Gốm Việt Handmade"),
    ("audiohanoi",  "audiohn@example.com",     "Nguyễn Âm Thanh", "Audio Hà Nội"),
    ("amthanhviet", "amthanh@example.com",     "Phạm Minh Loa",   "Âm Thanh Việt"),
]

# --------------------------------------------------------------------------
# Categories: parent -> children
# --------------------------------------------------------------------------
CATEGORIES = {
    "Gốm sứ":   ["Bát đĩa", "Ấm chén"],
    "Âm thanh": ["Ampli", "Loa"],
}

# (sku, category, seller, name, price_vnd, material, technique, note)
PRODUCTS = [
    # -- Bát đĩa: 8 products, 3 sellers. The working example for quartiles. ---
    ("BAT-001", "Bát đĩa", "gomthuha",  "Bát ăn cơm gốm sứ Bát Tràng men lam 12cm",            85_000, "Gốm", "Vuốt tay", None),
    ("BAT-002", "Bát đĩa", "gomthuha",  "Bát tô gốm Bát Tràng men rạn thủ công 20cm",          185_000, "Gốm", "Vuốt tay", None),
    ("BAT-003", "Bát đĩa", "gomthuha",  "Đĩa sứ trắng viền vàng cao cấp 25cm",                 145_000, "Sứ",  "Đổ khuôn", None),
    ("BAT-004", "Bát đĩa", "batrangvn", "Bát ăn cơm men xanh ngọc Bát Tràng 12cm",             120_000, "Gốm", "Vuốt tay", None),
    ("BAT-005", "Bát đĩa", "batrangvn", "Bộ 6 bát ăn cơm gốm sứ men lam vẽ tay",               280_000, "Gốm", "Vẽ tay",   None),
    ("BAT-006", "Bát đĩa", "batrangvn", "Đĩa gốm men hỏa biến thủ công 22cm",                  165_000, "Gốm", "Vuốt tay", None),
    ("BAT-007", "Bát đĩa", "gomviet",   "Bát tô lớn gốm men chảy nghệ thuật 24cm",             220_000, "Gốm", "Vuốt tay", None),
    # Priced far above its category on purpose -- gives "above market" a case,
    # and it is a legitimate price for a signed artist piece, which is exactly
    # why the screen must not scold the seller for it.
    ("BAT-008", "Bát đĩa", "gomviet",   "Bát nghệ thuật men hỏa biến ký tên nghệ nhân 28cm",   450_000, "Gốm", "Vuốt tay", None),

    # -- Ấm chén: only 3 products. BELOW MIN_COMPARABLE_N deliberately. -------
    ("AMC-001", "Ấm chén", "gomthuha",  "Bộ ấm chén trà gốm Bát Tràng men rạn 1 ấm 6 chén",    320_000, "Gốm", "Vuốt tay", None),
    ("AMC-002", "Ấm chén", "batrangvn", "Ấm trà tử sa khắc lá trúc thủ công 250ml",            299_000, "Gốm", "Khắc tay", None),
    ("AMC-003", "Ấm chén", "gomviet",   "Bộ ấm chén sứ trắng viền vàng 1 ấm 6 chén",           279_000, "Sứ",  "Đổ khuôn", None),

    # -- Ampli: real manufacturer model codes, across 3 sellers. -------------
    ("AMP-001", "Ampli", "audiohanoi",  "Ampli đèn mini Bluetooth Nobsound MS-10D MKIII",    3_589_000, None, None, None),
    ("AMP-002", "Ampli", "audiohanoi",  "Khuếch đại FX-Audio XL-2.1BL Bluetooth 4.0",        1_859_000, None, None, None),
    ("AMP-003", "Ampli", "audiohanoi",  "Ampli Bluetooth 5.3 kép TPA3116D2 công suất 200W",  1_459_000, None, None, None),
    ("AMP-004", "Ampli", "amthanhviet", "Ampli đèn Nobsound MS-10D MKIII chính hãng",        3_450_000, None, None, None),
    ("AMP-005", "Ampli", "amthanhviet", "Ampli mini SMSL AD18 80W Bluetooth DAC",            2_690_000, None, None, None),
    ("AMP-006", "Ampli", "amthanhviet", "Ampli Fosi Audio BT20A 100W x2 Bluetooth 5.0",        890_000, None, None, None),
    # Far below its category -- gives "below market" a case.
    ("AMP-007", "Ampli", "gomviet",     "Ampli đàn guitar mini JOYO JA-02 Amplifier",           290_000, None, None, None),

    # -- Loa -----------------------------------------------------------------
    ("LOA-001", "Loa", "audiohanoi",  "Loa Bluetooth JBL Grip JBLGRIP chính hãng",           3_990_000, None, None, None),
    ("LOA-002", "Loa", "audiohanoi",  "Loa Fender E12 Elie 12 công suất 120W Bluetooth 5.3", 8_999_000, None, None, None),
    ("LOA-003", "Loa", "audiohanoi",  "Loa Bluetooth Alpha Works AW-W89 chính hãng",         2_590_000, None, None, None),
    ("LOA-004", "Loa", "amthanhviet", "Loa Bluetooth JBL Grip JBLGRIP hàng chính hãng",      3_850_000, None, None, None),
    ("LOA-005", "Loa", "amthanhviet", "Loa Bluetooth di động USAMS YX015 BT5.3",               439_000, None, None, None),
    ("LOA-006", "Loa", "amthanhviet", "Loa Bluetooth Hoco HC22 mini để bàn",                   260_000, None, None, None),
]

# (sku, old_price, new_price) -- applied in order, so the trend has real shape.
# Written as a ledger the way services/product does it: origin row first, then
# one row per change, same transaction as the change itself.
PRICE_CHANGES = [
    ("BAT-002", 165_000, 185_000),
    ("BAT-005", 320_000, 280_000),
    ("AMP-001", 3_890_000, 3_589_000),
    ("AMP-004", 3_290_000, 3_450_000),
    ("LOA-001", 4_290_000, 3_990_000),
]


def seed(db, reset=False):
    if reset:
        skus = [SKU_PREFIX + p[0] for p in PRODUCTS]
        ids = [r.id for r in db.query(Product.id).filter(Product.sku.in_(skus)).all()]
        if ids:
            db.query(PriceHistory).filter(PriceHistory.product_id.in_(ids)).delete(
                synchronize_session=False
            )
            db.query(Product).filter(Product.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        print(f"  reset: removed {len(ids)} seeded products and their history")

    # -- sellers ---------------------------------------------------------
    sellers = {}
    hashed = get_password_hash(SEED_PASSWORD)
    for username, email, full_name, shop in SELLERS:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            user = User(
                username=username, email=email, full_name=full_name,
                hashed_password=hashed, role=UserRole.SELLER,
                is_active=True, is_verified=True, shop_name=shop,
                city="Hà Nội", country="Việt Nam",
            )
            db.add(user)
            db.flush()
            print(f"  + seller {username}")
        else:
            user.shop_name = user.shop_name or shop
            user.role = UserRole.SELLER
        sellers[username] = user
    db.commit()

    # -- categories ------------------------------------------------------
    cats = {}
    for parent_name, children in CATEGORIES.items():
        parent = db.query(Category).filter(
            Category.name == parent_name, Category.parent_id.is_(None)
        ).first()
        if parent is None:
            parent = Category(name=parent_name, is_active=True)
            db.add(parent)
            db.flush()
            print(f"  + category {parent_name}")
        cats[parent_name] = parent
        for child_name in children:
            child = db.query(Category).filter(
                Category.name == child_name, Category.parent_id == parent.id
            ).first()
            if child is None:
                child = Category(name=child_name, parent_id=parent.id, is_active=True)
                db.add(child)
                db.flush()
                print(f"  + category {parent_name} / {child_name}")
            cats[child_name] = child
    db.commit()

    # -- products, each with an origin row in the ledger ------------------
    added = updated = 0
    for sku, cat, seller, name, price, material, technique, _note in PRODUCTS:
        full_sku = SKU_PREFIX + sku
        product = db.query(Product).filter(Product.sku == full_sku).first()
        if product is None:
            product = Product(
                sku=full_sku,
                name=name,
                description=f"{name}. Hàng thủ công, giao toàn quốc." if material
                            else f"{name}. Bảo hành 12 tháng, giao toàn quốc.",
                price=Decimal(price),
                quantity_available=10,
                material=material,
                technique=technique,
                seller_id=sellers[seller].id,
                category_id=cats[cat].id,
                is_active=True,
            )
            db.add(product)
            db.flush()
            # Seed the origin row. Without it a "price at time T" reconstruction
            # before the first change returns nothing -- see
            # docs/ai-features/01-instrumentation.md PR 2.
            db.add(PriceHistory(
                product_id=product.id,
                old_price=Decimal(price), new_price=Decimal(price),
                change_reason="initial", changed_by=sellers[seller].id,
            ))
            added += 1
        else:
            product.price = Decimal(price)
            product.category_id = cats[cat].id
            product.is_active = True
            updated += 1
    db.commit()
    print(f"  products: {added} added, {updated} updated")

    # -- a few real price changes so the trend is not flat ----------------
    changes = 0
    for sku, old, new in PRICE_CHANGES:
        product = db.query(Product).filter(Product.sku == SKU_PREFIX + sku).first()
        if product is None:
            continue
        already = db.query(PriceHistory).filter(
            PriceHistory.product_id == product.id,
            PriceHistory.change_reason == "seller_update",
        ).first()
        if already:
            continue
        db.add(PriceHistory(
            product_id=product.id,
            old_price=Decimal(old), new_price=Decimal(new),
            change_reason="seller_update", changed_by=product.seller_id,
        ))
        changes += 1
    db.commit()
    print(f"  price_history: {changes} change rows added")


def report(db):
    """Show what phase 1 will actually see, using its own grouping."""
    from sqlalchemy import func as sa

    print("\n  category            products  sellers   min        median       max")
    print("  " + "-" * 68)
    rows = (
        db.query(
            Category.name,
            sa.count(Product.id),
            sa.count(sa.distinct(Product.seller_id)),
            sa.min(Product.price),
            sa.max(Product.price),
        )
        .join(Product, Product.category_id == Category.id)
        .filter(Product.is_active.is_(True))
        .group_by(Category.id, Category.name)
        .all()
    )
    for name, n, n_sellers, lo, hi in rows:
        prices = sorted(
            float(p[0]) for p in db.query(Product.price)
            .join(Category, Category.id == Product.category_id)
            .filter(Category.name == name, Product.is_active.is_(True)).all()
        )
        mid = prices[len(prices) // 2] if len(prices) % 2 else (
            prices[len(prices) // 2 - 1] + prices[len(prices) // 2]) / 2
        flag = "" if n >= 5 else "   <- below MIN_COMPARABLE_N, falls back to parent"
        print(f"  {name:<18} {n:>8} {n_sellers:>8}  {float(lo):>9,.0f}  "
              f"{mid:>10,.0f}  {float(hi):>9,.0f}{flag}")
    total = db.query(sa.count(Product.id)).filter(Product.is_active.is_(True)).scalar()
    hist = db.query(sa.count(PriceHistory.id)).scalar()
    print(f"\n  {total} active products, {hist} price_history rows")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true",
                    help="delete previously seeded products and history first")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not args.report_only:
            print("Seeding catalogue...")
            seed(db, reset=args.reset)
        report(db)
        print(f"\n  seller logins: {', '.join(s[0] for s in SELLERS)}")
        print(f"  password:      {SEED_PASSWORD}   (login takes the USERNAME, not the email)")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
