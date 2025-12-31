"""
Production Security Configuration

This module provides security configurations and utilities for
production deployment of the microservices.
"""
import os
import secrets
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class JWTConfig:
    """JWT Security Configuration"""
    # Token settings
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Key management
    secret_key: str = field(default_factory=lambda: os.getenv(
        "JWT_SECRET_KEY",
        secrets.token_urlsafe(64)
    ))

    # Validation settings
    require_exp: bool = True
    require_iat: bool = True
    verify_signature: bool = True
    leeway_seconds: int = 30

    # Token types
    access_token_type: str = "access"
    refresh_token_type: str = "refresh"


@dataclass
class PasswordConfig:
    """Password Security Configuration"""
    # Complexity requirements
    min_length: int = 12
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_characters: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Hashing
    algorithm: str = "bcrypt"
    bcrypt_rounds: int = 12

    # History
    password_history_count: int = 5
    password_max_age_days: int = 90


@dataclass
class RateLimitConfig:
    """Rate Limiting Configuration"""
    # Default limits
    default_requests_per_minute: int = 60
    default_requests_per_hour: int = 1000

    # Auth endpoints (stricter)
    auth_requests_per_minute: int = 10
    auth_requests_per_hour: int = 100

    # Login specific
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # API endpoints
    api_requests_per_second: int = 10
    api_burst_size: int = 50

    # Per-user limits
    user_requests_per_minute: int = 100
    user_requests_per_hour: int = 2000


@dataclass
class CORSConfig:
    """CORS Security Configuration"""
    # Production origins
    allowed_origins: List[str] = field(default_factory=lambda: [
        "https://stockhelper.com",
        "https://www.stockhelper.com",
        "https://app.stockhelper.com",
    ])

    # Methods
    allowed_methods: List[str] = field(default_factory=lambda: [
        "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
    ])

    # Headers
    allowed_headers: List[str] = field(default_factory=lambda: [
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-API-Key",
    ])

    # Credentials
    allow_credentials: bool = True

    # Cache
    max_age_seconds: int = 86400  # 24 hours


@dataclass
class TLSConfig:
    """TLS/SSL Configuration"""
    # TLS version
    min_version: str = "TLSv1.2"
    preferred_version: str = "TLSv1.3"

    # Cipher suites (TLS 1.3)
    ciphers: List[str] = field(default_factory=lambda: [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256",
    ])

    # Certificate settings
    cert_file: str = "/etc/ssl/certs/server.crt"
    key_file: str = "/etc/ssl/private/server.key"
    ca_file: str = "/etc/ssl/certs/ca-bundle.crt"

    # HSTS
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True


@dataclass
class InputValidationConfig:
    """Input Validation Configuration"""
    # Size limits
    max_request_size_mb: int = 10
    max_json_depth: int = 10
    max_string_length: int = 10000
    max_array_length: int = 1000

    # Content types
    allowed_content_types: List[str] = field(default_factory=lambda: [
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
    ])

    # SQL injection patterns
    sql_injection_patterns: List[str] = field(default_factory=lambda: [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",
        r"((\%27)|(\')|(\%22)|(\")|(\%2D\%2D)|(\-\-))",
    ])

    # XSS patterns
    xss_patterns: List[str] = field(default_factory=lambda: [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
    ])


@dataclass
class SessionConfig:
    """Session Security Configuration"""
    # Session settings
    session_timeout_minutes: int = 30
    session_max_age_hours: int = 24
    session_regenerate_on_auth: bool = True

    # Cookie settings
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "Strict"
    cookie_path: str = "/"
    cookie_domain: Optional[str] = None


@dataclass
class AuditConfig:
    """Audit Logging Configuration"""
    # Events to audit
    audit_events: List[str] = field(default_factory=lambda: [
        "login",
        "logout",
        "login_failed",
        "password_change",
        "permission_change",
        "data_access",
        "data_modification",
        "admin_action",
    ])

    # Log retention
    log_retention_days: int = 90
    sensitive_fields_to_mask: List[str] = field(default_factory=lambda: [
        "password",
        "token",
        "secret",
        "api_key",
        "credit_card",
        "ssn",
    ])


@dataclass
class SecurityHeaders:
    """HTTP Security Headers"""
    headers: Dict[str, str] = field(default_factory=lambda: {
        # XSS Protection
        "X-XSS-Protection": "1; mode=block",

        # Content Type Options
        "X-Content-Type-Options": "nosniff",

        # Frame Options
        "X-Frame-Options": "DENY",

        # Content Security Policy
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.stockhelper.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        ),

        # Referrer Policy
        "Referrer-Policy": "strict-origin-when-cross-origin",

        # Permissions Policy
        "Permissions-Policy": (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=()"
        ),

        # Cache Control for sensitive responses
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
    })


@dataclass
class ProductionSecurityConfig:
    """Complete Production Security Configuration"""
    jwt: JWTConfig = field(default_factory=JWTConfig)
    password: PasswordConfig = field(default_factory=PasswordConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    cors: CORSConfig = field(default_factory=CORSConfig)
    tls: TLSConfig = field(default_factory=TLSConfig)
    input_validation: InputValidationConfig = field(default_factory=InputValidationConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    headers: SecurityHeaders = field(default_factory=SecurityHeaders)


# Singleton instance
_security_config: Optional[ProductionSecurityConfig] = None


def get_security_config() -> ProductionSecurityConfig:
    """Get the security configuration singleton"""
    global _security_config
    if _security_config is None:
        _security_config = ProductionSecurityConfig()
    return _security_config


# Security validation functions
def validate_password(password: str, config: Optional[PasswordConfig] = None) -> Dict[str, Any]:
    """Validate password against security requirements"""
    config = config or get_security_config().password
    errors = []

    if len(password) < config.min_length:
        errors.append(f"Password must be at least {config.min_length} characters")

    if config.require_uppercase and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if config.require_lowercase and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if config.require_digit and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    if config.require_special and not any(c in config.special_characters for c in password):
        errors.append(f"Password must contain at least one special character")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def mask_sensitive_data(data: Dict[str, Any], config: Optional[AuditConfig] = None) -> Dict[str, Any]:
    """Mask sensitive fields in data for logging"""
    config = config or get_security_config().audit
    masked = {}

    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in config.sensitive_fields_to_mask):
            masked[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value, config)
        else:
            masked[key] = value

    return masked
