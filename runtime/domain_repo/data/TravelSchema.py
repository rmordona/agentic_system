from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import date

class Activity(BaseModel):
    time_slot: str # "Morning", "Afternoon", "Evening"
    description: str
    location: str
    confirmed: bool = False

class TravelSchema(BaseModel):
    """Schema for Vacation Planning and Itinerary Management"""
    destination: str
    start_date: date
    end_date: date
    budget_limit: float = Field(description="Total budget for the trip")
    currency: str = "USD"
    
    # Traveler Profile
    traveler_count: int = 1
    preferences: List[str] = Field(
        default_factory=list, 
        description="e.g., 'vegan', 'adventure', 'quiet hotels'"
    )
    
    # The Evolving Plan
    itinerary: Dict[str, List[Activity]] = Field(
        default_factory=dict,
        description="Key is ISO date string, value is list of activities"
    )
    
    # Logistics Status
    transport_booked: bool = False
    accommodation_booked: bool = False
    total_estimated_cost: float = 0.0
