"""
dependencies.py

FastAPI dependency providers.

Responsibilities:
- Extract authenticated user from request
- Validate JWT tokens
- Provide shared runtime dependencies

This module bridges FastAPI and security logic.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any

from app.core.security import decode_token

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> Dict[str, Any]:
    """
    Resolve the current authenticated user.

    This dependency:
    - Extracts JWT from Authorization header
    - Validates token
    - Returns user identity + roles

    Raises:
        401 Unauthorized if token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return payload
