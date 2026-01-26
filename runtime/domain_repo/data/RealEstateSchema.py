from pydantic import BaseModel, Field
from typing import List, Optional

class RealEstateSchema(BaseModel):
    """Schema for Property Evaluation and Market Analysis"""
    address: str = ""
    property_id: Optional[str] = None
    
    # Financials
    estimated_value: float = 0.0
    list_price: Optional[float] = None
    tax_assessment: float = 0.0
    
    # Specs
    bedrooms: int = 0
    bathrooms: float = 0.0
    square_footage: int = 0
    year_built: Optional[int] = None
    
    # Market Context
    comparable_sales: List[float] = Field(default_factory=list)
    neighborhood_rating: Optional[str] = None
