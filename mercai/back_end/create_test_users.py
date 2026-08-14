"""
Create test users for E2E testing with password "12345678"
"""

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User, UserRole

# Password for all test users: "12345678"
TEST_PASSWORD_HASH = "$2b$12$a.WBFT5EjkVGejaQxBhjuuDlAkpF6.X4iMR5rfGevo/Spl2xJGyCG"

def create_test_user(db: Session, user_data: dict):
    """Create or update a test user"""
    try:
        existing_user = db.query(User).filter(User.username == user_data['username']).first()

        if existing_user:
            print(f"✓ User {user_data['username']} already exists (ID: {existing_user.id})")
            if existing_user.hashed_password != TEST_PASSWORD_HASH:
                print(f"  Updating password for {user_data['username']}")
                existing_user.hashed_password = TEST_PASSWORD_HASH
                db.commit()
                print(f"  ✓ Password updated to '12345678'")
            return existing_user.id

        user = User(
            id=user_data['id'],
            email=user_data['email'],
            username=user_data['username'],
            hashed_password=TEST_PASSWORD_HASH,
            full_name=user_data['full_name'],
            phone_number=user_data['phone_number'],
            role=user_data['role'],
            is_active=True,
            is_verified=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"✓ Created user: {user_data['username']} (ID: {user.id}, Role: {user.role.value})")
        return user.id

    except Exception as e:
        print(f"✗ Error with user {user_data['username']}: {e}")
        db.rollback()
        raise

def main():
    print("Creating test users for E2E testing...")
    print("Password for all users: 12345678")
    print()

    test_users = [
        {
            'id': 500,
            'username': 'test_customer',
            'email': 'test_customer@example.com',
            'full_name': 'Test Customer',
            'phone_number': '+1234567500',
            'role': UserRole.CUSTOMER
        },
        {
            'id': 501,
            'username': 'test_seller',
            'email': 'test_seller@example.com',
            'full_name': 'Test Seller',
            'phone_number': '+1234567501',
            'role': UserRole.SELLER
        },
        {
            'id': 502,
            'username': 'test_dual',
            'email': 'test_dual@example.com',
            'full_name': 'Test Dual',
            'phone_number': '+1234567502',
            'role': UserRole.DUAL
        }
    ]

    db = SessionLocal()
    try:
        for user_data in test_users:
            create_test_user(db, user_data)

        print()
        print("=" * 60)
        print("✓ Test users ready!")
        print("=" * 60)
        print("Username: test_customer | Password: 12345678 | Role: CUSTOMER")
        print("Username: test_seller   | Password: 12345678 | Role: SELLER")
        print("Username: test_dual     | Password: 12345678 | Role: DUAL")
        print()

    finally:
        db.close()

if __name__ == "__main__":
    main()
