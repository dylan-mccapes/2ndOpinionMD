"""
Example script demonstrating how to query the Chroma database
for medical diagnoses using the 2ndOpinionMD-MVP project.
"""

import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vectordb.query_engine import MedicalQueryEngine

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(project_root, '.env')
    load_dotenv(env_path)
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    engine = MedicalQueryEngine(persist_directory="./chroma_db")
    
    symptoms = [
        "joint pain",
        "fatigue",
        "morning stiffness",
        "symmetric joint swelling"
    ]
    
    print(f"Querying for symptoms: {', '.join(symptoms)}")
    
    response = engine.generate_rag_response(symptoms, model="gpt-3.5-turbo")
    
    print("\nDiagnosis Results:")
    print(json.dumps(response, indent=2))
    
    print("\nQuerying specific collections:")
    
    disease_results = engine.query_collection("disease", f"Patient with {', '.join(symptoms)}", top_k=2)
    
    print("\nDisease Results:")
    for result in disease_results:
        print(f"\nDisease (Confidence: {result['confidence']}%):")
        print(result['text'])
    
    case_results = engine.query_collection("case", f"Patient with {', '.join(symptoms)}", top_k=2)
    
    print("\nCase Study Results:")
    for result in case_results:
        print(f"\nCase Study (Confidence: {result['confidence']}%):")
        print(result['text'])
    
    print("\nQuerying all collections:")
    all_results = engine.query_all_collections(f"Patient with {', '.join(symptoms)}", top_k=1)
    
    for collection_name, results in all_results.items():
        print(f"\n{collection_name.capitalize()} Results:")
        for result in results:
            print(f"\n{collection_name.capitalize()} (Confidence: {result['confidence']}%):")
            print(result['text'])
    
    print("\nDone! You can now use the MedicalQueryEngine to query your medical data.")

if __name__ == "__main__":
    main()
