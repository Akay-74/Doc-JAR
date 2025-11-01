import google.generativeai as genai
import os
import json
from typing import List, Dict, Any

GEMINI_API_KEY="AIzaSyBFfcQ8IxMAR2vO_sDDMY_HRltTQo050PE"
# Configure the API key
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    print("Error: GEMINI_API_KEY environment variable not set.")
    # The application will likely fail, but we'll let it try.
    # main.py's load_dotenv() should handle this.
except Exception as e:
    print(f"Error configuring Gemini: {e}")

# Set up the generative model
llm = genai.GenerativeModel('gemini-1.5-pro-latest')

def _call_gemini_json(prompt: str) -> Dict[str, Any]:
    """
    Helper function to call Gemini and parse its JSON output.
    Includes basic error handling.
    """
    try:
        response = llm.generate_content(prompt)
        # Clean up the response text before parsing
        cleaned_text = response.text.strip().lstrip("```json").rstrip("```")
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from Gemini response. Response was: {response.text}")
        return {"error": "JSONDecodeError", "details": str(e), "response_text": response.text}
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return {"error": "APIError", "details": str(e)}

def extract_entities(text: str, info: dict) -> dict:
    """Uses Gemini to parse the user's text and info."""
    prompt = f"""
    Parse the following patient information and return a structured JSON object.
    
    Patient Text: "{text}"
    Patient Info: {json.dumps(info)}
    
    Extract the following fields:
    1. "symptoms": A list of all medical symptoms.
    2. "pre_existing_conditions": A list of all permanent diseases or conditions (e.g., 'diabetes_type_2', 'chronic_kidney_disease', 'is_pregnant').
    3. "current_medications": A list of all medications the patient is currently taking.
    
    Return ONLY the JSON object.
    """
    return _call_gemini_json(prompt)

def get_differential_reasoning(symptoms: List[str], test_options: Dict[str, List[str]]) -> List[str]:
    """(Feature 9) Asks Gemini to decide which test to run."""
    prompt = f"""
    A patient has these symptoms: {", ".join(symptoms)}.
    The diagnosis is narrowed down to these possibilities, which require the following tests:
    {json.dumps(test_options, indent=2)}
    
    What specific tests should the patient be ordered to do to make a definitive diagnosis? 
    List the test names only. Return a JSON list of strings.
    
    Return ONLY the JSON list.
    """
    # This specific call expects a list, not a dict
    try:
        response = llm.generate_content(prompt)
        cleaned_text = response.text.strip().lstrip("```json").rstrip("```")
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"Error in get_differential_reasoning: {e}")
        return ["Error processing diagnostic tests"]


def run_safety_check(patient_profile: dict, drug_json: dict, symptoms: List[str]) -> dict:
    """(Features 3 & 8) The core safety check logic."""
    prompt = f"""
    You are an AI Clinical Pharmacist. Perform a safety check.
    
    Patient Profile:
    {json.dumps(patient_profile, indent=2)}
    
    Patient's Current Symptoms:
    {json.dumps(symptoms, indent=2)}
    
    Proposed Drug (Full JSON Data):
    {json.dumps(drug_json, indent=2)}
    
    Analyze the following and return a JSON object with keys "is_safe" (bool) and "conflict_reason" (str):
    
    1. (Feature 3) Check `contraindications.existing_diseases`: Do any of the patient's `pre_existing_conditions` match a `disease_id` listed here?
    2. (Feature 3) Check `contraindications.allergies`: Any conflicts?
    3. (Feature 3) Check `drug_interactions`: Do any of the patient's `current_medications` conflict?
    4. (Feature 8) Check `adverse_effects`: Does this drug have an adverse effect that is the *same as* one of the patient's *current symptoms*? (e.g., patient has nausea, drug also causes nausea). This could make the condition worse.
    
    If any check fails, set `is_safe` to false and provide a `conflict_reason` (e.g., "Drug is contraindicated for patient's condition: [condition]" or "Drug may worsen existing symptom: [symptom]").
    If all checks pass, set `is_safe` to true and `conflict_reason` to null.
    
    Return ONLY the JSON object.
    """
    return _call_gemini_json(prompt)

def get_full_treatment_plan(disease_json: dict, drug_json: dict, patient_info: dict) -> dict:
    """(Features 2, 4, 5, 7) Generates the final plan."""
    prompt = f"""
    You are an AI Clinical Assistant. Generate a complete, patient-friendly treatment plan.
    
    Patient Info: {json.dumps(patient_info)}
    Diagnosis: {disease_json.get('disease_name', 'N/A')}
    Prescribed Drug: {drug_json.get('generic_name', 'N/A')}
    
    Generate a JSON object with the following keys:
    
    1. "prescription" (object): A `Prescription` object with keys "medicine_name", "dosage", "frequency", and "duration". (e.g., 500mg, Twice a day, For 7 days). Use a standard dose.
    2. "lifestyle_and_diet" (list[str]): (Feature 4) A list of 3-5 bullet points for diet and lifestyle changes.
    3. "supportive_medicine" (list[str]): (Feature 5) A list of 1-2 *types* of precautionary medicine (e.g., "An antacid like Omeprazole for acidity", "An anti-emetic like Ondansetron for nausea").
    4. "follow_up_instructions" (str): (Feature 7) A single string on when/if to follow up or get tested again.
    
    Return ONLY the JSON object.
    """
    return _call_gemini_json(prompt)
