"""
Initialize test data for Ceramic Marketplace
This script ensures test accounts exist with consistent passwords across restarts
"""

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.product import Product, ProductImage
from app.models.address import ShippingAddress
from app.models.review import Review
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.seller_profile import StoreTheme
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# IMPORTANT: This is the bcrypt hash for password "Mysql_2025!"
# Generated once and reused to maintain consistency
CUSTOMER_A_PASSWORD_HASH = "$2b$12$UusiPB9I4cBUfcY3qmlk2.BtGOv.mCGCXXfLKfkXqyN.Ol/6DuZ5m"

def ensure_test_user_customer_a(db: Session):
    """
    Ensure customer_a test account exists with correct password and DUAL role
    This function is idempotent - it only creates/updates if needed
    """
    try:
        # Check if customer_a exists
        customer_a = db.query(User).filter(User.username == "customer_a").first()

        if customer_a:
            # User exists - verify password hash and role are correct
            needs_update = False

            if customer_a.hashed_password != CUSTOMER_A_PASSWORD_HASH:
                logger.info("Updating customer_a password hash to correct value")
                customer_a.hashed_password = CUSTOMER_A_PASSWORD_HASH
                needs_update = True

            # Ensure role is DUAL to allow role switching in tests
            if customer_a.role != UserRole.DUAL:
                logger.info(f"Updating customer_a role from {customer_a.role} to DUAL")
                customer_a.role = UserRole.DUAL
                needs_update = True

            if needs_update:
                db.commit()
                logger.info("✓ customer_a account updated")
            else:
                logger.info("✓ customer_a already has correct password and role")
        else:
            # User doesn't exist - create it with DUAL role
            logger.info("Creating customer_a test account with DUAL role")
            customer_a = User(
                id=100,
                email="customer_a@test.com",
                username="customer_a",
                hashed_password=CUSTOMER_A_PASSWORD_HASH,
                full_name="Customer A",
                phone_number="+1234567001",
                role=UserRole.DUAL,  # DUAL role allows switching between customer and seller
                is_active=True,
                is_verified=True
            )
            db.add(customer_a)
            db.commit()
            logger.info("✓ customer_a test account created")

    except Exception as e:
        logger.error(f"Error ensuring customer_a test account: {e}")
        db.rollback()
        raise

def ensure_product_stock(db: Session):
    """
    Ensure test products have sufficient stock for testing
    """
    try:
        # Update stock for commonly used test products
        # Product IDs: 1001 (product_A2), 1002, 1003, etc.
        product_ids_to_stock = [1001, 1002, 1003, 1004, 1005, 1050, 1051, 1052]

        updated_count = 0
        for product_id in product_ids_to_stock:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product and product.quantity_available < 20:
                product.quantity_available = 50  # Ensure sufficient stock
                updated_count += 1

        if updated_count > 0:
            db.commit()
            logger.info(f"✓ Updated stock for {updated_count} products")
        else:
            logger.info("✓ All products have sufficient stock")

    except Exception as e:
        logger.warning(f"Error ensuring product stock: {e}")
        db.rollback()

def ensure_customer_addresses(db: Session):
    """
    Ensure customer_a has some test addresses (but not the maximum)
    Creates 2 addresses to allow testing of Create/Update/Delete operations
    """
    try:
        # Check existing addresses for customer_a (user_id = 100)
        existing_addresses = db.query(ShippingAddress).filter(
            ShippingAddress.user_id == 100
        ).all()

        if len(existing_addresses) >= 2:
            logger.info(f"✓ customer_a already has {len(existing_addresses)} addresses")
            return

        # Create 2 test addresses if they don't exist
        # Using ID 1 and 2 to match test script expectations
        test_addresses = [
            {
                "id": 1,
                "user_id": 100,
                "title": "Home",
                "full_name": "Customer A",
                "phone_number": "+1234567001",
                "address_line1": "123 Main Street",
                "address_line2": "Apt 4B",
                "city": "New York",
                "state": "NY",
                "postal_code": "10001",
                "country": "USA",
                "is_default": True
            },
            {
                "id": 2,
                "user_id": 100,
                "title": "Work",
                "full_name": "Customer A",
                "phone_number": "+1234567001",
                "address_line1": "456 Office Boulevard",
                "city": "Brooklyn",
                "state": "NY",
                "postal_code": "11201",
                "country": "USA",
                "is_default": False
            }
        ]

        created_count = 0
        for addr_data in test_addresses:
            # Check if address with this ID already exists
            existing = db.query(ShippingAddress).filter(
                ShippingAddress.id == addr_data["id"]
            ).first()

            if not existing:
                address = ShippingAddress(**addr_data)
                db.add(address)
                created_count += 1

        if created_count > 0:
            db.commit()
            logger.info(f"✓ Created {created_count} test addresses for customer_a")
        else:
            logger.info("✓ Test addresses already exist")

    except Exception as e:
        logger.warning(f"Error ensuring customer addresses: {e}")
        db.rollback()

def cleanup_test_reviews(db: Session):
    """
    Clean up specific reviews that conflict with test cases
    The test suite expects to create a review for product_id=1002, order_id=2013
    """
    try:
        # Delete existing review for product_id=1002 and order_id=2013 if it exists
        # This allows the "Create Review" test to run successfully
        existing_review = db.query(Review).filter(
            Review.product_id == 1002,
            Review.order_id == 2013,
            Review.reviewer_id == 100
        ).first()

        if existing_review:
            logger.info("Removing conflicting review for product_id=1002, order_id=2013")
            db.delete(existing_review)
            db.commit()
            logger.info("✓ Conflicting review removed")
        else:
            logger.info("✓ No conflicting reviews found")

    except Exception as e:
        logger.warning(f"Error cleaning up test reviews: {e}")
        db.rollback()

def ensure_seller_bulk_operation_products(db: Session):
    """
    Ensure seller_a has products with IDs 1, 2, 3 for bulk operation testing
    These products are specifically used by bulk update status and bulk price update tests
    """
    try:
        from app.models.product import Category

        # Get a default category (use category 100 or create one)
        category = db.query(Category).filter(Category.id == 100).first()
        if not category:
            category = db.query(Category).first()

        if not category:
            logger.warning("No categories found, cannot create bulk operation test products")
            return

        # Products to ensure exist for seller_a (user_id = 200)
        test_products = [
            {
                "id": 1,
                "name": "Bulk Test Product 1",
                "description": "Test product for bulk operations",
                "price": 29.99,
                "quantity_available": 50,
                "category_id": category.id,
                "seller_id": 200,
                "is_active": True,
                "is_featured": False,
                "sku": "BULK-TEST-001"
            },
            {
                "id": 2,
                "name": "Bulk Test Product 2",
                "description": "Test product for bulk operations",
                "price": 39.99,
                "quantity_available": 50,
                "category_id": category.id,
                "seller_id": 200,
                "is_active": True,
                "is_featured": False,
                "sku": "BULK-TEST-002"
            },
            {
                "id": 3,
                "name": "Bulk Test Product 3",
                "description": "Test product for bulk operations",
                "price": 49.99,
                "quantity_available": 50,
                "category_id": category.id,
                "seller_id": 200,
                "is_active": True,
                "is_featured": False,
                "sku": "BULK-TEST-003"
            }
        ]

        created_count = 0
        updated_count = 0

        for product_data in test_products:
            existing = db.query(Product).filter(Product.id == product_data["id"]).first()

            if existing:
                # Update if seller_id doesn't match
                if existing.seller_id != 200:
                    logger.info(f"Updating product {product_data['id']} to belong to seller_a")
                    for key, value in product_data.items():
                        if key != "id":
                            setattr(existing, key, value)
                    updated_count += 1
            else:
                # Create new product
                product = Product(**product_data)
                db.add(product)
                created_count += 1

        if created_count > 0 or updated_count > 0:
            db.commit()
            logger.info(f"✓ Bulk operation products: created {created_count}, updated {updated_count}")
        else:
            logger.info("✓ Bulk operation test products already exist")

    except Exception as e:
        logger.warning(f"Error ensuring bulk operation products: {e}")
        db.rollback()

def ensure_order_2000_test_data(db: Session):
    """
    Ensure order 2000 is properly configured for fulfillment tests
    - Set status to CONFIRMED (allows transition to processing, then shipped)
    - Reset payment_status to COMPLETED (allows refund test to run)
    - Ensure it has product_id 1 in order items (for return request test)
    - Set total amount >= $45.99 (for refund test)
    """
    try:
        # Check if order 2000 exists
        order = db.query(Order).filter(Order.id == 2000).first()

        if not order:
            logger.warning("Order 2000 not found, cannot configure for tests")
            return

        needs_update = False

        # Fix order status - should be CONFIRMED to allow testing status transitions
        if order.status != OrderStatus.CONFIRMED:
            logger.info(f"Updating order 2000 status from {order.status} to CONFIRMED")
            order.status = OrderStatus.CONFIRMED
            needs_update = True

        # Reset payment_status to COMPLETED - allows refund test to run
        # (Process Return Request test sets it to REFUNDED, blocking Process Refund test)
        if order.payment_status != PaymentStatus.COMPLETED:
            logger.info(f"Resetting order 2000 payment_status from {order.payment_status} to COMPLETED")
            order.payment_status = PaymentStatus.COMPLETED
            needs_update = True

        # Ensure order total is sufficient for refund test (>= $45.99)
        if float(order.total_amount) < 45.99:
            logger.info(f"Updating order 2000 total from {order.total_amount} to 50.00")
            order.total_amount = Decimal("50.00")
            order.subtotal = Decimal("45.00")
            order.tax_amount = Decimal("3.00")
            order.shipping_amount = Decimal("2.00")
            needs_update = True

        # Check if order has product_id 1 in its items (needed for return request test)
        has_product_1 = any(item.product_id == 1 for item in order.items)

        if not has_product_1:
            logger.info("Adding product_id 1 to order 2000 items for return request test")

            # Get product 1 details
            product = db.query(Product).filter(Product.id == 1).first()
            if product:
                # Add order item with product 1
                new_item = OrderItem(
                    order_id=2000,
                    product_id=1,
                    product_name=product.name,
                    product_description=product.description,
                    quantity=1,
                    unit_price=Decimal("29.99"),
                    total_price=Decimal("29.99")
                )
                db.add(new_item)
                needs_update = True

        if needs_update:
            db.commit()
            logger.info("✓ Order 2000 configured for fulfillment tests")
        else:
            logger.info("✓ Order 2000 already properly configured")

    except Exception as e:
        logger.warning(f"Error configuring order 2000: {e}")
        db.rollback()

def ensure_theme_test_data(db: Session):
    """
    Ensure seller_a has test themes:
    - Theme 2: Inactive theme for activation testing
    - Theme 3: Inactive theme specifically for deletion testing
    """
    try:
        from app.models.seller_profile import SellerProfile

        # Get seller_a's profile
        seller_profile = db.query(SellerProfile).filter(
            SellerProfile.user_id == 200
        ).first()

        if not seller_profile:
            logger.warning("Seller profile for user_id 200 not found, cannot create theme")
            return

        # Ensure theme 2 exists and is inactive (for activation test)
        theme_2 = db.query(StoreTheme).filter(StoreTheme.id == 2).first()
        if not theme_2:
            logger.info("Creating inactive theme 2 for activation test")
            theme_2 = StoreTheme(
                id=2,
                seller_profile_id=seller_profile.id,
                theme_name="Test Theme 2",
                primary_color="#000000",
                secondary_color="#FFFFFF",
                is_active=False
            )
            db.add(theme_2)
        else:
            # Reset theme 2 to inactive
            if theme_2.is_active:
                logger.info("Resetting theme 2 to inactive")
                theme_2.is_active = False

        # Ensure theme 3 exists and is inactive (specifically for deletion test)
        theme_3 = db.query(StoreTheme).filter(StoreTheme.id == 3).first()
        if not theme_3:
            logger.info("Creating inactive theme 3 for deletion test")
            theme_3 = StoreTheme(
                id=3,
                seller_profile_id=seller_profile.id,
                theme_name="Test Theme for Deletion",
                primary_color="#FF0000",
                secondary_color="#0000FF",
                is_active=False
            )
            db.add(theme_3)
        else:
            # Ensure theme 3 is inactive
            if theme_3.is_active:
                logger.info("Resetting theme 3 to inactive")
                theme_3.is_active = False

        db.commit()
        logger.info("✓ Test themes configured (2: for activation, 3: for deletion)")

    except Exception as e:
        logger.warning(f"Error ensuring theme test data: {e}")
        db.rollback()

def ensure_product_images(db: Session):
    """
    Ensure product 1050 has exactly 4 test images with correct IDs
    This allows image management tests to work properly
    """
    try:
        # Clean up all existing images for product 1050
        db.query(ProductImage).filter(ProductImage.product_id == 1050).delete()
        db.commit()

        # Create exactly 4 images with known IDs
        test_images = [
            {"id": 46, "product_id": 1050, "image_url": "https://example.com/images/product_1050_1.jpg",
             "alt_text": "Product 1050 - Image 1", "is_primary": False, "order_index": 0},
            {"id": 47, "product_id": 1050, "image_url": "https://example.com/images/product_1050_2.jpg",
             "alt_text": "Product 1050 - Image 2", "is_primary": True, "order_index": 1},
            {"id": 48, "product_id": 1050, "image_url": "https://example.com/images/product_1050_3.jpg",
             "alt_text": "Product 1050 - Image 3", "is_primary": False, "order_index": 2},
            {"id": 49, "product_id": 1050, "image_url": "https://example.com/images/product_1050_4.jpg",
             "alt_text": "Product 1050 - Image 4", "is_primary": False, "order_index": 3},
        ]

        for img_data in test_images:
            image = ProductImage(**img_data)
            db.add(image)

        db.commit()
        logger.info("✓ Created 4 test images for product 1050 (IDs: 46, 47, 48, 49)")

    except Exception as e:
        logger.warning(f"Error ensuring product images: {e}")
        db.rollback()

def initialize_test_data():
    """
    Initialize essential test data
    This is called on application startup to ensure test accounts exist
    """
    logger.info("Initializing test data...")

    db = SessionLocal()
    try:
        # Ensure customer_a test account exists with correct password and DUAL role
        ensure_test_user_customer_a(db)

        # Ensure products have sufficient stock for testing
        ensure_product_stock(db)

        # Ensure seller_a has products for bulk operation testing (IDs 1, 2, 3)
        ensure_seller_bulk_operation_products(db)

        # Ensure customer_a has test addresses
        ensure_customer_addresses(db)

        # Clean up conflicting reviews to allow test cases to run
        cleanup_test_reviews(db)

        # Ensure product 1050 has correct test images
        ensure_product_images(db)

        # Ensure order 2000 is configured for fulfillment tests
        ensure_order_2000_test_data(db)

        # Ensure theme test data is available
        ensure_theme_test_data(db)

        logger.info("✓ Test data initialization completed")

    except Exception as e:
        logger.error(f"✗ Error initializing test data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    initialize_test_data()
