from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=1, max_length=50, description="Username must be between 1 and 50 characters")
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name is required")
    phone_number: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError("Username cannot be empty or whitespace only")
        # Allow alphanumeric, underscores, and hyphens
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v.strip()
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Full name cannot be empty or whitespace only")
        return v.strip()
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v is not None and v.strip():
            # Basic phone validation - digits, spaces, hyphens, parentheses, and plus sign
            import re
            if not re.match(r'^[\d\s\-\(\)\+]+$', v):
                raise ValueError("Phone number contains invalid characters")
        return v.strip() if v else v

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    
    @validator('password')
    def validate_password(cls, v):
        from app.core.security import validate_password
        validation_result = validate_password(v)
        if not validation_result["is_valid"]:
            raise ValueError("; ".join(validation_result["errors"]))
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    shop_name: Optional[str] = None
    shop_description: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    shop_name: Optional[str] = None
    shop_description: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class PasswordReset(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        from app.core.security import validate_password
        validation_result = validate_password(v)
        if not validation_result["is_valid"]:
            raise ValueError("; ".join(validation_result["errors"]))
        return v

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @validator('new_password')
    def validate_new_password(cls, v):
        from app.core.security import validate_password
        validation_result = validate_password(v)
        if not validation_result["is_valid"]:
            raise ValueError("; ".join(validation_result["errors"]))
        return v

class EmailVerification(BaseModel):
    token: str

class RoleSwitch(BaseModel):
    new_role: UserRole