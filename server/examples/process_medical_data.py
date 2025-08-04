"""
Example script demonstrating how to process medical data JSON files
for the 2ndOpinionMD-MVP project.
"""

import os
import json
import sys
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.utils.normalized_data_processor import process_medical_data_file

def main():
    
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
    
    print("\nProcessed data structure:")
    for item in processed_data:
        print(f"- Type: {item['type']}, ID: {item['id']}")
        print(f"  Text preview: {item['text'][:100]}...")
    
    print("\nDone! You can now use the normalized_data_processor.py module to process your medical data.")
    print("Note: ChromaDB functionality has been removed. Use PostgreSQL + pgvector for vector search.")

if __name__ == "__main__":
    main()
