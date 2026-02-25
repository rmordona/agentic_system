"""
rbac.py

Role-Based Access Control utilities.

Responsibilities:
- Enforce authorization rules
- Validate role membership
- Centralize permission logic

This module is intentionally lightweight.
"""

from fastapi import HTTPException, status
from typing import Dict, List


def require_role(user: Dict, role: str):
    """
    Enforce that a user has a specific role.

    Args:
        user: Decoded JWT payload
        role: Required role name

    Raises:
        403 Forbidden if role is missing
    """
    roles: List[str] = user.get("roles", [])

    if role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' required",
        )


def require_any_role(user: Dict, roles: List[str]):
    """
    Enforce that a user has at least one of the specified roles.

    Args:
        user: Decoded JWT payload
        roles: List of acceptable roles

    Raises:
        403 Forbidden if none are present
    """
    user_roles = set(user.get("roles", []))

    if not user_roles.intersection(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"One of roles {roles} required",
        )
