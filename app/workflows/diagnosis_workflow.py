from app.services import gemini_service, json_db_service
from app.models import PatientInput

def run_diagnostic(input_data: PatientInput) -> dict:
    """Implements Features 1 & 9."""
    
    # 1. Parse user input
    profile = gemini_service.extract_entities(input_data.symptoms_text, input_data.patient_info or {})
    if 'error' in profile:
        print(f"Error extracting entities: {profile['details']}")
        return {"status": "ERROR", "message": "Failed to parse input with AI."}
        
    symptoms = profile.get("symptoms", [])
    if not symptoms:
        print("No symptoms extracted from input.")
        return {"status": "NO_MATCH", "profile": profile}

    # 2. Search for diseases
    disease_results = json_db_service.search_diseases_by_symptoms(symptoms)
    
    if not disease_results:
        print("No disease matches found in vector search.")
        return {"status": "NO_MATCH", "profile": profile}
    
    # 3. Check Confidence (Feature 1)
    top_disease_id, top_score = disease_results[0]
    
    # Simple confidence logic: high if score > 0.8 and 20% > next best
    is_confident = False
    if top_score > 0.8:
        if len(disease_results) == 1 or (top_score - disease_results[1][1] > 0.2):
            is_confident = True
    # Loosen confidence for demo purposes if top score is decent
    elif top_score > 0.65 and len(disease_results) > 1 and (top_score - disease_results[1][1] > 0.15):
         is_confident = True
    elif top_score > 0.5 and len(disease_results) == 1:
        is_confident = True
            
    if is_confident:
        disease_json = json_db_service.get_disease_details(top_disease_id)
        if not disease_json:
             return {"status": "NO_MATCH", "profile": profile} # Failed to read file
        
        return {
            "status": "CONFIRMED",
            "diagnosis": disease_json.get('disease_name', 'Unknown Disease'),
            "diagnosis_id": top_disease_id,
            "confidence": top_score,
            "profile": profile,
            "symptoms": symptoms
        }
    else:
        # Feature 9: Get data for follow-up tests
        test_options = {}
        for disease_id, score in disease_results[:3]: # Get top 3 candidates
            disease_data = json_db_service.get_disease_details(disease_id)
            if disease_data:
                test_names = [test['test_name'] for test in disease_data.get('diagnostic_tests', [])]
                if test_names: # Only include if tests are listed
                    test_options[disease_data.get('disease_name', disease_id)] = test_names
        
        if not test_options:
            # No tests found for candidates, just return inconclusive
             return {
                "status": "NEEDS_DATA",
                "required_tests": ["Further clinical evaluation needed."]
            }

        required_tests = gemini_service.get_differential_reasoning(symptoms, test_options)
        return {
            "status": "NEEDS_DATA",
            "required_tests": required_tests
        }
