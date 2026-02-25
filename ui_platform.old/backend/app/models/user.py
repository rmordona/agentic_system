"""
user.py

User domain models.

Responsibilities:
- Represent authenticated platform users
- Encode RBAC roles
- Support developer vs user execution modes

This file contains ONLY domain models.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class User(BaseModel):
    """
    Core user identity model.

    Used across:
    - Authentication
    - Authorization
    - Audit logging
    """

    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    roles: List[str] = Field(default_factory=list, description="RBAC roles")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(BaseModel):
    """
    Payload for us
