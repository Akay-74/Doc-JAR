from app.services import gemini_service, json_db_service
from app.models import FinalDiagnosisReport, Prescription

def get_treatment_plan(diag_result: dict, patient_info: dict) -> FinalDiagnosisReport:
    """Implements Features 2, 3, 4, 5, 6, 7, 8."""
    
    diagnosis_name = diag_result['diagnosis']
    diagnosis_id = diag_result['diagnosis_id']
    confidence = diag_result['confidence']
    profile = diag_result['profile']
    symptoms = diag_result['symptoms']
    
    # Get all possible medicines for the disease
    medicine_ids = json_db_service.search_medicines_by_disease(diagnosis_id)
    
    if not medicine_ids:
        # No medicine found in local JSONs
        print(f"No medicine found for diagnosis ID: {diagnosis_id}")
        return FinalDiagnosisReport(
            diagnosis=diagnosis_name,
            confidence_score=confidence,
            follow_up_tests_required=None,
            contraindication_warning=f"No suitable medicine found in the local database for {diagnosis_name}."
        )

    # --- Safety Loop (Features 3 & 8) ---
    safe_drug_json = None
    first_drug_conflict_reason = None
    
    for med_id in medicine_ids:
        drug_json = json_db_service.get_medicine_details(med_id)
        if not drug_json:
            print(f"Could not load details for medicine ID: {med_id}")
            continue # Skip this medicine

        safety_report = gemini_service.run_safety_check(profile, drug_json, symptoms)
        if 'error' in safety_report:
             print(f"Error during safety check for {med_id}: {safety_report['details']}")
             continue # Skip this medicine
        
        if safety_report.get('is_safe', False):
            safe_drug_json = drug_json
            break # Found a safe drug
        elif not first_drug_conflict_reason:
            # Store the conflict reason for the *first* drug we tried
            first_drug_conflict_reason = safety_report.get('conflict_reason', 'Unknown conflict')
    
    if not safe_drug_json:
        # We looped through all and none were safe
        print(f"No safe drug found for {diagnosis_name} among {medicine_ids}")
        return FinalDiagnosisReport(
            diagnosis=diagnosis_name,
            confidence_score=confidence,
            follow_up_tests_required=None,
            contraindication_warning=f"All available treatments are contraindicated. Reason for first drug checked: {first_drug_conflict_reason}"
        )
    # -------------------------------------

    # We have a safe drug, now get the full plan
    disease_json = json_db_service.get_disease_details(diagnosis_id)
    plan_data = gemini_service.get_full_treatment_plan(disease_json, safe_drug_json, patient_info)
    
    if 'error' in plan_data:
        print(f"Error getting full treatment plan: {plan_data['details']}")
        # Return with basic info, but no plan
        return FinalDiagnosisReport(
            diagnosis=diagnosis_name,
            confidence_score=confidence,
            follow_up_tests_required=None,
            prescription=Prescription(medicine_name=safe_drug_json.get('generic_name', 'N/A'), dosage="N/A", frequency="N/A", duration="N/A"),
            contraindication_warning="Failed to generate detailed plan."
        )

    # Check if this was an alternative
    try:
        main_prescription = Prescription(**plan_data['prescription'])
    except Exception as e:
        print(f"Error parsing prescription from Gemini: {e}")
        main_prescription = Prescription(medicine_name=safe_drug_json.get('generic_name', 'N/A'), dosage="See doctor", frequency="See doctor", duration="See doctor")

    alt_prescription = None
    warning = None
    
    if first_drug_conflict_reason:
        # This means the first drug failed, and we are using an alternative
        warning = f"Note: First-line drug was contraindicated ({first_drug_conflict_reason}). Prescribing alternative."
        alt_prescription = main_prescription
        main_prescription = None # No "main" prescription, only the alternative

    # Assemble the final 9-point report
    report = FinalDiagnosisReport(
        # Feature 1
        diagnosis=diagnosis_name,
        confidence_score=confidence,
        
        # Feature 9
        follow_up_tests_required=None,
        
        # Feature 2 & 3
        prescription=main_prescription,
        contraindication_warning=warning,
        alternative_prescription=alt_prescription,
        
        # Feature 8
        adverse_effect_warning=None, # This is bundled into the contraindication_warning by the safety check logic
        
        # Feature 4
        lifestyle_and_diet=plan_data.get('lifestyle_and_diet'),
        
        # Feature 5
        supportive_medicine=plan_data.get('supportive_medicine'),
        
        # Feature 6
        general_side_effect_note="If you experience severe swelling, irritation, or nausea, stop taking all medication and consult a doctor immediately.",
        
        # Feature 7
        follow_up_instructions=plan_data.get('follow_up_instructions')
    )
    
    return report
