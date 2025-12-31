from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    create_email_verification_token,
    generate_password_reset_token
)
from app.core.config import settings
from datetime import datetime, timedelta

class AuthService:
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/email and password"""
        # Try to find by username first, then by email
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user
    
    @staticmethod
    def create_user_tokens(user: User) -> dict:
        """Create access and refresh tokens for user"""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": user.username})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @staticmethod
    def register_user(
        db: Session, 
        email: str, 
        username: str, 
        password: str, 
        full_name: str,
        phone_number: Optional[str] = None,
        role: UserRole = UserRole.CUSTOMER
    ) -> User:
        """Register a new user"""
        # Check if email exists
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username exists
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create user
        hashed_password = get_password_hash(password)
        verification_token = create_email_verification_token(email)
        
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            phone_number=phone_number,
            role=role,
            email_verification_token=verification_token
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def initiate_password_reset(db: Session, email: str) -> Optional[str]:
        """Initiate password reset for user"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        reset_token = generate_password_reset_token()
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        return reset_token
    
    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> bool:
        """Reset user password with token"""
        user = db.query(User).filter(
            User.password_reset_token == token,
            User.password_reset_expires > datetime.utcnow()
        ).first()
        
        if not user:
            return False
        
        user.hashed_password = get_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.commit()
        
        return True
    
    @staticmethod
    def verify_email(db: Session, token: str, email: str) -> bool:
        """Verify user email with token"""
        user = db.query(User).filter(User.email == email).first()
        if not user or user.email_verification_token != token:
            return False
        
        user.is_verified = True
        user.email_verification_token = None
        db.commit()
        
        return True
    
    @staticmethod
    def change_user_role(db: Session, user: User, new_role: UserRole) -> bool:
        """Change user role with validation"""
        # Validate role transition
        valid_transitions = {
            UserRole.CUSTOMER: [UserRole.SELLER, UserRole.DUAL],
            UserRole.SELLER: [UserRole.CUSTOMER, UserRole.DUAL],
            UserRole.DUAL: [UserRole.CUSTOMER, UserRole.SELLER]
        }
        
        if new_role not in valid_transitions.get(user.role, []):
            return False
        
        user.role = new_role
        db.commit()
        return True