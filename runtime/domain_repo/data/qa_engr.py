from pydantic import BaseModel, Field
from typing import List, Dict, Union

class TestResult(BaseModel):
    test_id: str
    status: str # "pass", "fail", "skipped"
    duration_ms: float
    error_message: Optional[str] = None

class QaSchema(BaseModel):
    """Schema for Quality Assurance and Validation Evidence"""
    suite_name: str = Field(description="The name of the test suite executed")
    total_tests: int
    passed_tests: int
    failed_tests: int
    
    # Detailed Evidence
    test_details: List[TestResult] = Field(default_factory=list)
    coverage_percentage: float = Field(ge=0, le=100)
    
    # Bug Tracking
    bugs_discovered: List[Dict[str, Union[str, int]]] = Field(
        default_factory=list, 
        description="List of bugs: {'severity': 'high', 'desc': '...'}"
    )
    is_safe_to_deploy: bool = False
