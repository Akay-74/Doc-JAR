from fastapi import FastAPI, HTTPException
from app.models import PatientInput, FinalDiagnosisReport
from app.services import json_db_service
from app.workflows import diagnosis_workflow, treatment_workflow
import os
from dotenv import load_dotenv

# Load environment variables (GEMINI_API_KEY)
# This should be at the top, before services are imported (though services load it too)
load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    print("FATAL ERROR: GEMINI_API_KEY is not set. Please create a .env file.")
    # The app will fail, but this print makes it clear why.

app = FastAPI(
    title="AI Clinical Decision Support System",
    description="Accepts patient data and returns a 9-point diagnosis and treatment plan."
)

@app.on_event("startup")
async def startup_event():
    """
    On server startup, load and index all JSON data into the
    ChromaDB vector store.
    """
    print("Server starting up...")
    # Ensure data directories exist before initializing
    if not os.path.exists("data/diseases") or not os.path.exists("data/medicines"):
        print("Warning: 'data/diseases' or 'data/medicines' directory not found.")
        print("Please create them and add JSON files.")
    
    json_db_service.initialize_database(
        disease_dir="data/diseases",
        medicine_dir="data/medicines"
    )
    print("Database initialization complete.")

@app.post("/analyze", response_model=FinalDiagnosisReport)
async def analyze_patient(input_data: PatientInput):
    """
    Main endpoint to analyze a patient.
    Accepts the PatientInput JSON and returns the 9-point FinalDiagnosisReport.
    """
    try:
        # --- Run Diagnosis Workflow (Features 1 & 9) ---
        diag_result = diagnosis_workflow.run_diagnostic(input_data)
        
        if diag_result['status'] == "NEEDS_DATA":
            # Feature 9: Not enough data
            return FinalDiagnosisReport(
                diagnosis="Inconclusive",
                confidence_score=0.0,
                follow_up_tests_required=diag_result['required_tests']
            )
            
        if diag_result['status'] == "NO_MATCH":
            return FinalDiagnosisReport(
                diagnosis="No match found",
                confidence_score=0.0,
                follow_up_tests_required=["Symptoms do not match known conditions in the database. Please consult a doctor."]
            )
        
        if diag_result['status'] == "ERROR":
            raise HTTPException(status_code=500, detail=diag_result.get("message", "Error in diagnosis workflow."))

        # --- Run Treatment Workflow (Features 2-8) ---
        patient_info = input_data.patient_info or {}
        full_report = treatment_workflow.get_treatment_plan(diag_result, patient_info)
        
        return full_report

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Log the full traceback
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# To run the server: uvicorn app.main:app --reload
