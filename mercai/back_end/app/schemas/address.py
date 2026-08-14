from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class ShippingAddressBase(BaseModel):
    title: str
    full_name: str
    phone_number: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"

class ShippingAddressCreate(ShippingAddressBase):
    is_default: bool = False
    
    @validator('title')
    def validate_title(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Title must be at least 2 characters')
        return v.strip()
    
    @validator('phone_number')
    def validate_phone(cls, v):
        # Basic phone validation
        import re
        phone_pattern = r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'
        if not re.match(phone_pattern, v.replace(' ', '')):
            raise ValueError('Invalid phone number format')
        return v
    
    @validator('postal_code')
    def validate_postal_code(cls, v):
        # Basic US postal code validation
        import re
        if not re.match(r'^\d{5}(-\d{4})?$', v):
            raise ValueError('Invalid postal code format')
        return v

class ShippingAddressUpdate(BaseModel):
    title: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_default: Optional[bool] = None
    
    @validator('title')
    def validate_title(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Title must be at least 2 characters')
        return v.strip() if v else v
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if v is not None:
            import re
            phone_pattern = r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'
            if not re.match(phone_pattern, v.replace(' ', '')):
                raise ValueError('Invalid phone number format')
        return v
    
    @validator('postal_code')
    def validate_postal_code(cls, v):
        if v is not None:
            import re
            if not re.match(r'^\d{5}(-\d{4})?$', v):
                raise ValueError('Invalid postal code format')
        return v

class ShippingAddressResponse(ShippingAddressBase):
    id: int
    user_id: int
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True