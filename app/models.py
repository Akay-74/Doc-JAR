from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
GEMINI_API_KEY="AIzaSyBFfcQ8IxMAR2vO_sDDMY_HRltTQo050PE"
# MODEL FOR THE USER'S INPUT JSON
class PatientInput(BaseModel):
    symptoms_text: str = Field(..., description="Unstructured text of patient symptoms, e.g., 'Had a fever for 5 days'")
    lab_reports: Optional[Dict[str, Any]] = Field(None, description="Structured lab data, e.g., {'WBC': 15000}")
    patient_info: Optional[Dict[str, Any]] = Field(None, description="e.g., {'age': 45, 'is_pregnant': false, 'permanent_diseases': ['diabetes_type_2']}")

# SUB-MODEL FOR PRESCRIPTIONS
class Prescription(BaseModel):
    medicine_name: str
    dosage: str = Field(..., description="e.g., '500mg'")
    frequency: str = Field(..., description="e.g., 'Twice a day'")
    duration: str = Field(..., description="e.g., 'For 7 days'")

# MODEL FOR THE 9-POINT FINAL OUTPUT JSON
class FinalDiagnosisReport(BaseModel):
    # Feature 1: Diagnosis & Confidence
    diagnosis: str
    confidence_score: float = Field(..., description="Confidence from 0.0 to 1.0")

    # Feature 9: Follow-up Tests
    follow_up_tests_required: Optional[List[str]] = Field(None, description="If data is not enough, list tests here.")

    # Feature 2: Prescription
    prescription: Optional[Prescription] = None

    # Feature 3: Contraindication Warning & Alternative
    contraindication_warning: Optional[str] = Field(None, description="Warning about permanent diseases/pregnancy.")
    alternative_prescription: Optional[Prescription] = Field(None, description="Alternative if main drug is contraindicated.")
    
    # Feature 8: Adverse Effect Warning
    adverse_effect_warning: Optional[str] = Field(None, description="Warning if drug promotes current symptoms.")

    # Feature 4: Lifestyle Advice
    lifestyle_and_diet: Optional[List[str]] = Field(None, description="Things to do/avoid, e.g., 'No oily food'.")

    # Feature 5: Supportive Medicine
    supportive_medicine: Optional[List[str]] = Field(None, description="Precautionary medicine for nausea, acidity, etc.")

    # Feature 6: General Side Effects
    general_side_effect_note: Optional[str] = Field(None, description="Standard warning to stop medicine if severe reaction.")

    # Feature 7: Follow-up Instructions
    follow_up_instructions: Optional[str] = Field(None, description="Instructions on when to re-test or follow up.")
