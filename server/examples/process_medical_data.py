"""
Example script demonstrating how to process medical data JSON files
and load them into Chroma for the 2ndOpinionMD-MVP project.
"""

import os
import json
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.normalized_data_processor import process_medical_data_file
import chromadb
from chromadb.utils import embedding_functions

def main():
    load_dotenv()
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    os.makedirs("examples/data", exist_ok=True)
    
    case_study = {
        "case_id": "AIDx-0002",
        "primary_condition": "Rheumatoid Arthritis",
        "diagnostic_zone": 3,
        "stax_score": 3,
        "flare_type": "Pathologic",
        "symptom_timeline": [
            "Intermittent aching pain and stiffness in small hand joints, worse in the morning",
            "Persistent symmetric joint swelling and warmth in wrists and fingers, with prolonged morning stiffness",
            "Increasing fatigue and difficulty with daily tasks due to joint pain",
            "Spread of arthritis to larger joints (knees, ankles) over time",
            "Joint deformities begin to appear in fingers after years of uncontrolled inflammation"
        ],
        "misdiagnosed_as": [
            "Osteoarthritis",
            "Fibromyalgia",
            "Lupus"
        ]
    }
    
    with open("examples/data/case_study_example.json", "w") as f:
        json.dump(case_study, f, indent=2)
    
    disease_profile = {
        "DiseaseName": "Myasthenia Gravis (MG)",
        "IcdCode": "G70.00",
        "CommonSymptoms": [
            "Intermittent muscle weakness that worsens with activity and improves with rest",
            "Drooping eyelids (ptosis) and double vision (diplopia), often the first signs"
        ]
    }
    
    with open("examples/data/disease_profile_example.json", "w") as f:
        json.dump(disease_profile, f, indent=2)
    
    disease_profile2 = {
        "diseaseName": "Lupus",
        "icdCode": "M32.9",
        "commonSymptoms": [
            "Butterfly-shaped rash across cheeks and nose",
            "Joint pain, stiffness and swelling"
        ]
    }
    
    with open("examples/data/disease_profile_camelcase_example.json", "w") as f:
        json.dump(disease_profile2, f, indent=2)
    
    underrepresented_profile = {
        "name": "Stiff Person Syndrome (SPS)",
        "icd10": "G25.82",
        "prevalence": "Estimated ~1 per 1,000,000 (0.0001%) in the general population",
        "symptom_profile": {
            "early_indicators": "Gradual onset of muscle stiffness in the trunk or limbs"
        }
    }
    
    with open("examples/data/underrepresented_profile_example.json", "w") as f:
        json.dump(underrepresented_profile, f, indent=2)
    
    combined_data = {
        "case_studies": [case_study],
        "DiseaseProfiles": [disease_profile],
        "diseaseProfiles": [disease_profile2],
        "underrepresentedAutoimmune": [underrepresented_profile]
    }
    
    with open("examples/data/combined_examples.json", "w") as f:
        json.dump(combined_data, f, indent=2)
    
    print("Example data files created in examples/data/ directory")
    
    processed_data = process_medical_data_file("examples/data/combined_examples.json")
    
    print(f"Processed {len(processed_data)} items from the combined examples file")
    
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name="text-embedding-3-small"
    )
    
    os.makedirs("examples/chroma_db", exist_ok=True)
    
    client = chromadb.PersistentClient(path="examples/chroma_db")
    
    collection = client.get_or_create_collection(
        name="medical_data",
        embedding_function=openai_ef
    )
    
    ids = [item['id'] for item in processed_data]
    documents = [item['text'] for item in processed_data]
    metadatas = [item['metadata'] for item in processed_data]
    
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    
    print(f"Added {len(processed_data)} items to the Chroma collection")
    
    query_text = "What are the symptoms of Myasthenia Gravis?"
    results = collection.query(
        query_texts=[query_text],
        n_results=2
    )
    
    print("\nExample Query Results:")
    print(f"Query: {query_text}")
    for i, doc_id in enumerate(results["ids"][0]):
        print(f"\nResult {i+1} (ID: {doc_id}):")
        print(results["documents"][0][i])
    
    print("\nDone! You can now use the normalized_data_processor.py module to process your medical data.")

if __name__ == "__main__":
    main()
