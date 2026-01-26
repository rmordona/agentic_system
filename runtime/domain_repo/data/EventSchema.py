from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class EventSchema(BaseModel):
    """Schema for Event Planning, Logistics, and Vendor Management"""
    
    # Core Identity
    event_name: str = ""
    event_type: str = "Corporate"  # e.g., Conference, Wedding, Gala
    venue_name: Optional[str] = None
    venue_address: str = ""
    
    # Logistics & Capacity
    guest_count_estimate: int = 0
    max_capacity_threshold: int = Field(0, description="Hard limit for the selected venue")
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    # Financials
    total_budget: float = 0.0
    allocated_spend: float = 0.0
    vendor_fees: Dict[str, float] = Field(default_factory=dict, description="Mapping of service name to cost")
    
    # Requirements & Compliance
    catering_requirements: List[str] = Field(default_factory=list)
    av_technical_needs: List[str] = Field(default_factory=list)
    permit_status: Optional[str] = "Pending"  # Pending, Approved, Not Required
    
    # Risk & Context
    is_outdoor: bool = False
    weather_contingency_plan: bool = False
    security_detail_required: bool = False
