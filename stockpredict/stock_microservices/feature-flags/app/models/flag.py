"""
Feature Flag Data Models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class FlagStatus(str, Enum):
    """Feature flag status"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    PERCENTAGE = "percentage"


class TargetType(str, Enum):
    """Target type for flag evaluation"""
    ALL = "all"
    USER = "user"
    GROUP = "group"
    PERCENTAGE = "percentage"


class FeatureFlag(BaseModel):
    """Feature flag configuration"""
    name: str = Field(..., description="Flag identifier")
    enabled: bool = Field(True, description="Whether flag is enabled")
    percentage: int = Field(0, ge=0, le=100, description="Traffic percentage (0-100)")
    description: str = Field("", description="Flag description")
    service: Optional[str] = Field(None, description="Target microservice")
    django_path: Optional[str] = Field(None, description="Django endpoint path")
    microservice_path: Optional[str] = Field(None, description="Microservice endpoint path")
    user_whitelist: List[str] = Field(default_factory=list, description="Whitelisted user IDs")
    group_whitelist: List[str] = Field(default_factory=list, description="Whitelisted groups")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FlagUpdate(BaseModel):
    """Flag update request"""
    enabled: Optional[bool] = None
    percentage: Optional[int] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    user_whitelist: Optional[List[str]] = None
    group_whitelist: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class FlagEvaluation(BaseModel):
    """Result of flag evaluation"""
    flag_name: str
    enabled: bool
    use_microservice: bool
    reason: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class EvaluationContext(BaseModel):
    """Context for flag evaluation"""
    user_id: Optional[str] = None
    user_groups: List[str] = Field(default_factory=list)
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class CutoverPhase(BaseModel):
    """Cutover phase configuration"""
    name: str
    description: str
    week: int
    percentages: Dict[str, int]


class CutoverStatus(BaseModel):
    """Current cutover status"""
    current_phase: str
    phase_info: CutoverPhase
    flags: Dict[str, FeatureFlag]
    health_status: str
    last_updated: datetime


class AuditLogEntry(BaseModel):
    """Audit log entry for flag changes"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str
    flag_name: str
    previous_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    actor: str = "system"
    reason: Optional[str] = None


class BulkUpdateRequest(BaseModel):
    """Bulk update request for phase transitions"""
    phase: str = Field(..., description="Target phase name")
    reason: Optional[str] = Field(None, description="Reason for change")
    dry_run: bool = Field(False, description="Simulate without applying")


class BulkUpdateResponse(BaseModel):
    """Response for bulk update"""
    success: bool
    phase: str
    changes: List[Dict[str, Any]]
    dry_run: bool
    applied_at: Optional[datetime] = None
