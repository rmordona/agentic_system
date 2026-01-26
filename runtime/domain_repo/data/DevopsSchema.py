from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from enum import Enum

class DeploymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK = "rollback"

class DevopsSchema(BaseModel):
    """Schema for Infrastructure and CI/CD Operations"""
    project_id: str = Field(description="The unique name of the service or repository")
    environment: str = Field(description="Target env: e.g., 'staging', 'production'")
    commit_sha: str = Field(description="The git hash being processed")
    
    # Infrastructure state
    resources: List[Dict[str, str]] = Field(
        default_factory=list, 
        description="List of cloud resources (e.g., {'type': 's3', 'name': 'logs-bucket'})"
    )
    
    # Deployment tracking
    status: DeploymentStatus = DeploymentStatus.PENDING
    logs_url: Optional[str] = None
    
    # Metadata for the next stage
    tags: Dict[str, str] = Field(default_factory=dict)
