"""
API Routes for Auth Service
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List

from app.models.domain import User
from app.models.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefresh,
    TokenVerify,
    TokenVerifyResponse,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    MessageResponse,
    ErrorResponse,
)
from app.services.auth_service import AuthService
from app.api.dependencies import (
    get_auth_service,
    get_current_user,
    get_client_info,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "User already exists"},
    },
)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.

    - **email**: Valid email address (unique)
    - **username**: Alphanumeric username (unique, 3-100 chars)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    - **full_name**: Optional full name
    """
    try:
        user, message = await auth_service.register(user_data)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
    },
)
async def login(
    login_data: UserLogin,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate user and return access/refresh tokens.

    - **email**: User's email address
    - **password**: User's password
    """
    client_info = get_client_info(request)
    try:
        tokens = await auth_service.login(
            login_data,
            user_agent=client_info["user_agent"],
            ip_address=client_info["ip_address"],
        )
        return tokens
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid refresh token"},
    },
)
async def refresh_token(
    token_data: TokenRefresh,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token from login
    """
    client_info = get_client_info(request)
    try:
        tokens = await auth_service.refresh_tokens(
            token_data.refresh_token,
            user_agent=client_info["user_agent"],
            ip_address=client_info["ip_address"],
        )
        return tokens
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
)
async def logout(
    token_data: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logout user by revoking refresh token.

    - **refresh_token**: Refresh token to revoke
    """
    success = await auth_service.logout(token_data.refresh_token)
    if success:
        return MessageResponse(message="Logged out successfully")
    return MessageResponse(message="Token not found or already revoked", success=False)


@router.post(
    "/logout-all",
    response_model=MessageResponse,
)
async def logout_all(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logout user from all devices by revoking all refresh tokens.

    Requires authentication.
    """
    count = await auth_service.logout_all(current_user.id)
    return MessageResponse(message=f"Logged out from {count} device(s)")


@router.post(
    "/verify",
    response_model=TokenVerifyResponse,
)
async def verify_token(
    token_data: TokenVerify,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Verify if a token is valid.

    - **token**: JWT access token to verify
    """
    return await auth_service.verify_token(token_data.token)


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user information.

    Requires authentication via Bearer token.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid current password"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Change current user's password.

    - **current_password**: Current password for verification
    - **new_password**: New password (min 8 chars, uppercase, lowercase, digit)

    Requires authentication. Will logout from all devices after password change.
    """
    try:
        success = await auth_service.change_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password,
        )
        if success:
            return MessageResponse(message="Password changed successfully")
        return MessageResponse(message="Failed to change password", success=False)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
async def reset_password(
    reset_data: PasswordReset,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Request password reset.

    - **email**: Email address for password reset

    Will send reset instructions if email exists (does not reveal if email exists).
    """
    message = await auth_service.request_password_reset(reset_data.email)
    return MessageResponse(message=message)


@router.post(
    "/reset-password/confirm",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired token"},
    },
)
async def reset_password_confirm(
    confirm_data: PasswordResetConfirm,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Confirm a password reset using the token issued by /reset-password.

    - **token**: JWT issued by request endpoint (sent via email)
    - **new_password**: New password (same complexity rules as registration)

    On success all existing sessions for the user are revoked.
    """
    try:
        success = await auth_service.confirm_password_reset(
            confirm_data.token,
            confirm_data.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reset password",
        )
    return MessageResponse(message="Password reset successfully")
