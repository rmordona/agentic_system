"""
auth.py

Authentication and authorization endpoints for the UI Platform.

Responsibilities:
- User login
- Token issuance (JWT)
- Identity verification
- Role propagation (developer / user / admin)

This module does NOT manage users at scale (delegated to IAM in production).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import create_token
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """
    Authenticate a user and issue a JWT.

    In production:
    - Replace with OAuth2 / SSO / OIDC
    - Validate credentials against IAM

    Returns:
        JWT token with embedded roles and user id.
    """
    if payload.username != "admin" or payload.password != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_token(
        {
            "sub": payload.username,
            "roles": ["developer", "user"],
        }
    )

    return TokenResponse(access_token=token)
