from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

class DiagnosisItem(BaseModel):
    diagnosis: str
    confidence_score: Optional[Union[str, float]] = None
    icd_10_code: Optional[str] = Field(default=None, alias="ICD-10_code")
    recommendations: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

class DiagnoseResponse(BaseModel):
    diagnoses: List[DiagnosisItem]
    
    model_config = ConfigDict(populate_by_name=True)
