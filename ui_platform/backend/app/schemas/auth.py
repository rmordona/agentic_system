# -----------------------------------------------------------------------------
# Project: Agentic System UI Platform
# File: ui_platform/backend/app/schemas/auth.py
#
# Description:
#   Authentication and authorization API schemas.
#
#   This module defines request/response contracts for:
#     - user login
#     - user registration
#     - JWT access tokens
#     - refresh tokens
#     - authentication status checks
#
#   These schemas:
#     - are UI-facing and safe
#     - never expose secrets or password hashes
#     - provide a stable contract for frontend clients
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-04
# -----------------------------------------------------------------------------

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# -----------------------------------------------------------------------------
# Login / Registration
# -----------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """
    Request payload for user login.

    Used by:
      POST /auth/login
    """

    email: EmailStr = Field(..., description="Registered user email")
    password: str = Field(..., description="Plaintext password")


class RegisterRequest(BaseModel):
    """
    Request payload for user registration.

    Used by:
      POST /auth/register

    Note:
      Passwords are never returned or logged.
    """

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Plaintext password")
    roles: List[str] = Field(
        default_factory=lambda: ["user"],
        description="Initial RBAC roles assigned to the user",
    )


# -----------------------------------------------------------------------------
# Token Schemas
# -----------------------------------------------------------------------------

class TokenPayload(BaseModel):
    """
    JWT payload schema.

    This schema mirrors the contents of a decoded JWT.
    """

    sub: str = Field(..., description="User ID")
    email: EmailStr
    roles: List[str]
    exp: int = Field(..., description="Expiration timestamp (epoch seconds)")


class TokenResponse(BaseModel):
    """
    Response returned after successful authentication.

    Used by:
      POST /auth/login
      POST /auth/refresh
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(..., description="Token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """
    Request payload for refreshing an access token.
    """

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """
    Response payload after refreshing a token.
    """

    access_token: str
    token_type: str = Field(default="bearer")
    expires_in: int


# -----------------------------------------------------------------------------
# Auth Status / Introspection
# -----------------------------------------------------------------------------

class AuthStatusResponse(BaseModel):
    """
    Response schema for checking current authentication state.

    Used by:
      GET /auth/me
    """

    user_id: str
    email: EmailStr
    roles: List[str]
    is_authenticated: bool = True


# -----------------------------------------------------------------------------
# Logout
# -------------
