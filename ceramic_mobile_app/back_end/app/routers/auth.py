from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password, 
    create_access_token, 
    create_refresh_token,
    create_email_verification_token,
    verify_token, 
    get_password_hash,
    generate_password_reset_token
)
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate, 
    UserResponse, 
    Token, 
    TokenRefresh,
    UserLogin,
    PasswordReset,
    PasswordResetRequest,
    EmailVerification,
    RoleSwitch
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(token, "access")
    if token_data is None:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == token_data["username"]).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

def get_user_from_token(token: str, db: Session) -> User:
    """Get user from token without raising HTTP exceptions (for WebSocket use)"""
    try:
        token_data = verify_token(token, "access")
        if token_data is None:
            return None
            
        user = db.query(User).filter(User.username == token_data["username"]).first()
        if user is None or not user.is_active:
            return None
        return user
    except Exception:
        return None

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_verified_user(current_user: User = Depends(get_current_active_user)):
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email address."
        )
    return current_user

optional_oauth2_scheme = HTTPBearer(auto_error=False)

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None

    try:
        token_data = verify_token(credentials.credentials, "access")
        if token_data is None:
            return None

        user = db.query(User).filter(User.username == token_data["username"]).first()
        if user is None or not user.is_active:
            return None
        return user
    except:
        return None

# Email sending function placeholder
async def send_verification_email(email: str, token: str):
    # TODO: Implement actual email sending
    print(f"Verification email would be sent to {email} with token {token}")

async def send_password_reset_email(email: str, token: str):
    # TODO: Implement actual email sending  
    print(f"Password reset email would be sent to {email} with token {token}")

@router.post("/register", response_model=UserResponse)
async def register_user(
    user: UserCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Check if email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    # Check if username already exists
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    verification_token = create_email_verification_token(user.email)
    
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
        email_verification_token=verification_token
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Send verification email
    background_tasks.add_task(send_verification_email, user.email, verification_token)
    
    return db_user

@router.post("/login", response_model=Token)
def login_for_access_token(
    user_credentials: UserLogin, 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == user_credentials.username).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is deactivated"
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token, 
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/refresh", response_model=Token)
def refresh_access_token(token_refresh: TokenRefresh, db: Session = Depends(get_db)):
    token_data = verify_token(token_refresh.refresh_token, "refresh")
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = db.query(User).filter(User.username == token_data["username"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
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

@router.post("/verify-email")
def verify_email(verification: EmailVerification, db: Session = Depends(get_db)):
    token_data = verify_token(verification.token, "email_verification")
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user = db.query(User).filter(User.email == token_data["username"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_verified = True
    user.email_verification_token = None
    db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/resend-verification")
async def resend_verification_email(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    verification_token = create_email_verification_token(current_user.email)
    current_user.email_verification_token = verification_token
    db.commit()
    
    background_tasks.add_task(send_verification_email, current_user.email, verification_token)
    
    return {"message": "Verification email sent"}

@router.post("/forgot-password")
async def forgot_password(
    password_reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == password_reset_request.email).first()
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a password reset link has been sent"}
    
    reset_token = generate_password_reset_token()
    user.password_reset_token = reset_token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    background_tasks.add_task(send_password_reset_email, user.email, reset_token)
    
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password")
def reset_password(password_reset: PasswordReset, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.password_reset_token == password_reset.token,
        User.password_reset_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user.hashed_password = get_password_hash(password_reset.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()
    
    return {"message": "Password reset successfully"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.post("/switch-role")
def switch_user_role(
    role_switch: RoleSwitch,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    if role_switch.new_role == current_user.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already in the requested role"
        )
    
    # Validate role transition
    valid_transitions = {
        UserRole.CUSTOMER: [UserRole.SELLER, UserRole.DUAL],
        UserRole.SELLER: [UserRole.CUSTOMER, UserRole.DUAL], 
        UserRole.DUAL: [UserRole.CUSTOMER, UserRole.SELLER]
    }
    
    if role_switch.new_role not in valid_transitions[current_user.role]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role transition"
        )
    
    current_user.role = role_switch.new_role
    db.commit()
    
    return {"message": f"Role switched to {role_switch.new_role}"}

@router.post("/logout")
def logout():
    # For JWT tokens, logout is handled client-side by discarding the token
    # In a production system, you might want to maintain a blacklist of tokens
    # No authentication required - client just needs to discard the token
    return {"message": "Logged out successfully"}