import chromadb
import json
import os
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
# Initialize ChromaDB client and embedding model
# Using PersistentClient to save the DB to disk in the './chroma_db' directory
try:
    client = chromadb.PersistentClient(path="./chroma_db")
except Exception as e:
    print(f"Failed to initialize ChromaDB client: {e}")
    # Fallback to in-memory if persistent fails (e.g., permissions)
    client = chromadb.Client()

try:
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    print(f"Failed to load SentenceTransformer model: {e}")
    # Handle model loading failure gracefully
    raise

# Create/get collections
disease_collection = client.get_or_create_collection(name="diseases")
medicine_collection = client.get_or_create_collection(name="medicines")

def initialize_database(disease_dir: str, medicine_dir: str):
    """
    Called once at startup. Scans, embeds, and indexes all local JSON files.
    """
    print("Initializing database...")
    
    # 1. Index Diseases
    try:
        if not os.path.exists(disease_dir):
            print(f"Warning: Disease directory not found: {disease_dir}")
            return
            
        for filename in os.listdir(disease_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(disease_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    disease_id = data['disease_id']
                    
                    # Create a searchable document for each symptom
                    documents = []
                    metadatas = []
                    doc_ids = []
                    
                    for i, symptom in enumerate(data.get('symptoms', [])):
                        doc_text = f"Symptom: {symptom.get('name', '')} - {symptom.get('details', '')}. Disease: {data.get('disease_name', '')}"
                        documents.append(doc_text)
                        metadatas.append({"disease_id": disease_id})
                        doc_ids.append(f"{disease_id}_symptom_{i}")
                    
                    if documents:
                        embeddings = embedding_model.embed_documents(documents)
                        disease_collection.add(embeddings=embeddings, documents=documents, metadatas=metadatas, ids=doc_ids)
        print(f"Indexed {disease_collection.count()} disease symptoms.")
    except Exception as e:
        print(f"Error indexing diseases: {e}")

    # 2. Index Medicines
    try:
        if not os.path.exists(medicine_dir):
            print(f"Warning: Medicine directory not found: {medicine_dir}")
            return

        for filename in os.listdir(medicine_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(medicine_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    medicine_id = data['drug_id']
                    
                    # Create a searchable document for each indication (disease it treats)
                    documents = []
                    metadatas = []
                    doc_ids = []
                    
                    for i, indication_id in enumerate(data.get('indications', [])):
                        doc_text = f"Treats disease with ID: {indication_id}"
                        documents.append(doc_text)
                        metadatas.append({"medicine_id": medicine_id, "disease_id": indication_id})
                        doc_ids.append(f"{medicine_id}_indication_{i}")
                    
                    if documents:
                        embeddings = embedding_model.embed_documents(documents)
                        medicine_collection.add(embeddings=embeddings, documents=documents, metadatas=metadatas, ids=doc_ids)
        print(f"Indexed {medicine_collection.count()} medicine indications.")
    except Exception as e:
        print(f"Error indexing medicines: {e}")

def search_diseases_by_symptoms(symptoms: List[str]) -> List[tuple[str, float]]:
    """
    Queries ChromaDB to find the most likely diseases based on symptoms.
    Returns: A list of (disease_id, score) tuples.
    """
    if not symptoms:
        return []
        
    query_text = "Patient symptoms: " + ", ".join(symptoms)
    query_embedding = embedding_model.embed_query(query_text)
    
    try:
        results = disease_collection.query(query_embeddings=[query_embedding], n_results=5)
    except Exception as e:
        print(f"Error querying disease collection: {e}")
        return []

    # Aggregate scores for each unique disease_id
    disease_scores = {}
    if 'metadatas' in results and 'distances' in results and results['metadatas']:
        for i, meta in enumerate(results['metadatas'][0]):
            disease_id = meta['disease_id']
            distance = results['distances'][0][i]
            score = 1.0 - distance # Convert distance to similarity score
            if disease_id not in disease_scores:
                disease_scores[disease_id] = 0
            disease_scores[disease_id] += score
    
    return sorted(disease_scores.items(), key=lambda item: item[1], reverse=True)

def search_medicines_by_disease(disease_id: str) -> List[str]:
    """
    Queries ChromaDB to find medicines that treat a specific disease_id.
    Returns: A list of medicine_id strings.
    """
    try:
        results = medicine_collection.query(
            where={"disease_id": disease_id},
            n_results=10
        )
    except Exception as e:
        print(f"Error querying medicine collection: {e}")
        return []
        
    medicine_ids = set()
    if 'metadatas' in results and results['metadatas']:
        medicine_ids = {meta['medicine_id'] for meta in results['metadatas'][0]}
        
    return list(medicine_ids)

def get_disease_details(disease_id: str) -> dict:
    """Reads and returns the full JSON for a single disease."""
    filepath = f"data/diseases/{disease_id}.json"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Disease file not found: {filepath}")
        return {}
    except Exception as e:
        print(f"Error reading disease file {filepath}: {e}")
        return {}

def get_medicine_details(medicine_id: str) -> dict:
    """Reads and returns the full JSON for a single medicine."""
    filepath = f"data/medicines/{medicine_id}.json"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Medicine file not found: {filepath}")
        return {}
    except Exception as e:
        print(f"Error reading medicine file {filepath}: {e}")
        return {}
