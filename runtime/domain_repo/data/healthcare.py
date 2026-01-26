from pydantic import BaseModel, Field
from typing import Dict, List

class HealthcareSchema(BaseModel):
    """The 'Naked' Schema provided by the Domain Dev"""
    patient_id: str
    vitals: Dict[str, float] = Field(default_factory=dict)
    diagnosis_codes: List[str] = Field(default_factory=list)
