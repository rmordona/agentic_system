from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class DevSchema(BaseModel):
    """Schema for Software Engineering and Feature Implementation"""
    branch_name: str = Field(description="The git branch for the feature")
    files_changed: List[str] = Field(default_factory=list, description="Paths to modified files")
    pull_request_url: Optional[str] = None
    
    # Technical Metadata
    dependencies_added: List[str] = Field(default_factory=list)
    architectural_notes: str = Field(description="Summary of implementation decisions")
    
    # Task Tracking
    is_build_passing: bool = False
    technical_debt_incured: List[str] = Field(default_factory=list, description="Known shortcuts taken")
