"""
security.py

Authentication and token security utilities.

Responsibilities:
- JWT creation
- JWT verification
- Token payload validation
- Cryptographic guarantees

This module MUST NOT depend on FastAPI.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import jwt

from app.core.config import get_settings

settings = get_settings()


def create_token(payload: Dict[str, Any]) -> str:
    """
    Create a signed JWT token.

    Args:
        payload: Dictionary containing user identity and roles

    Returns:
        Encoded JWT token string
    """
    expiration = datetime.utcnow() + timedelta(
        seconds=settings.JWT_EXPIRATION_SECONDS
    )

    token_payload = {
        **payload,
        "exp": expiration,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(
        token_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT string

    Returns:
        Decoded payload

    Raises:
        jwt.PyJWTError if token is invalid or expired
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
