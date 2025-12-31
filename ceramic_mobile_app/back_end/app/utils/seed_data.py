"""
Seed data for Ceramic Marketplace database
Creates initial sample data for testing and development
"""

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.product import Category
from passlib.context import CryptContext
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_default_categories(db: Session):
    """Create default product categories"""
    default_categories = [
        {"name": "Vases", "description": "Decorative and functional ceramic vases"},
        {"name": "Bowls", "description": "Ceramic bowls for various uses"},
        {"name": "Plates", "description": "Dinner plates and decorative plates"},
        {"name": "Mugs & Cups", "description": "Coffee mugs, tea cups, and drinkware"},
        {"name": "Decorative Items", "description": "Ceramic decorations and art pieces"},
        {"name": "Planters", "description": "Ceramic planters and pots"},
        {"name": "Tiles", "description": "Ceramic tiles for flooring and walls"},
        {"name": "Figurines", "description": "Ceramic figurines and sculptures"},
    ]

    created_count = 0
    for cat_data in default_categories:
        # Check if category already exists
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            category = Category(**cat_data)
            db.add(category)
            created_count += 1

    if created_count > 0:
        db.commit()
        logger.info(f"✓ Created {created_count} default categories")
    else:
        logger.info("✓ Categories already exist")

def create_test_users(db: Session):
    """Create test users for development"""
    test_users = [
        {
            "email": "admin@ceramic.com",
            "username": "admin",
            "password": "admin123",
            "full_name": "Admin User",
            "role": UserRole.DUAL,
            "is_verified": True,
            "shop_name": "Admin Ceramics",
            "shop_description": "Premium handcrafted ceramics",
        },
        {
            "email": "seller@ceramic.com",
            "username": "seller1",
            "password": "seller123",
            "full_name": "Seller User",
            "role": UserRole.SELLER,
            "is_verified": True,
            "shop_name": "Artisan Ceramics",
            "shop_description": "Traditional ceramic artwork",
        },
        {
            "email": "customer@ceramic.com",
            "username": "customer1",
            "password": "customer123",
            "full_name": "Customer User",
            "role": UserRole.CUSTOMER,
            "is_verified": True,
        },
    ]

    created_count = 0
    for user_data in test_users:
        # Check if user already exists
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing:
            # Hash password
            password = user_data.pop("password")
            hashed_password = pwd_context.hash(password)

            user = User(
                **user_data,
                hashed_password=hashed_password,
                created_at=datetime.utcnow()
            )
            db.add(user)
            created_count += 1

    if created_count > 0:
        db.commit()
        logger.info(f"✓ Created {created_count} test users")
    else:
        logger.info("✓ Test users already exist")

def seed_database():
    """Run all seed data functions"""
    logger.info("Starting database seeding...")

    db = SessionLocal()
    try:
        # Create categories
        create_default_categories(db)

        # Create test users
        create_test_users(db)

        logger.info("✓ Database seeding completed successfully")

    except Exception as e:
        logger.error(f"✗ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
