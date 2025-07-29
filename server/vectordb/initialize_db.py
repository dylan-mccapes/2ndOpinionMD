import os
import sys
import json
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("OPENAI_API_KEY environment variable not set. Using placeholder for demo.")
    openai_api_key = "sk-placeholder"

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_api_key,
    model_name="text-embedding-3-small"
)

def initialize_chroma_db(persist_directory="./chroma_db"):
    """
    Initialize ChromaDB with sample data for testing
    """
    print(f"Initializing ChromaDB at {persist_directory}")
    
    os.makedirs(persist_directory, exist_ok=True)
    
    client = chromadb.PersistentClient(path=persist_directory)
    
    disease_collection = client.get_or_create_collection(
        name="disease",
        embedding_function=openai_ef
    )
    
    citation_collection = client.get_or_create_collection(
        name="citation",
        embedding_function=openai_ef
    )
    
    diseases = [
        {
            "id": "disease_1",
            "text": "Rheumatoid Arthritis (RA): An autoimmune disorder that primarily affects the joints. Symptoms include joint pain, swelling, stiffness (especially in the morning), fatigue, and sometimes fever. RA typically affects joints symmetrically and can lead to joint deformity if untreated.",
            "metadata": {
                "name": "Rheumatoid Arthritis",
                "category": "autoimmune",
                "affected_systems": "joints, sometimes lungs and heart",
                "common_tests": "RF, anti-CCP, ESR, CRP"
            }
        },
        {
            "id": "disease_2",
            "text": "Systemic Lupus Erythematosus (SLE): A chronic autoimmune disease that can affect multiple body systems. Common symptoms include fatigue, joint pain, rash (especially the butterfly rash across the face), fever, and photosensitivity. SLE can affect the skin, joints, kidneys, brain, and other organs.",
            "metadata": {
                "name": "Systemic Lupus Erythematosus",
                "category": "autoimmune",
                "affected_systems": "skin, joints, kidneys, brain, heart",
                "common_tests": "ANA, anti-dsDNA, complement levels"
            }
        },
        {
            "id": "disease_3",
            "text": "Multiple Sclerosis (MS): An autoimmune disease affecting the central nervous system. Symptoms vary widely but can include fatigue, numbness or weakness in limbs, vision problems, tremor, and problems with coordination and balance.",
            "metadata": {
                "name": "Multiple Sclerosis",
                "category": "autoimmune",
                "affected_systems": "central nervous system",
                "common_tests": "MRI, lumbar puncture, evoked potential tests"
            }
        },
        {
            "id": "disease_4",
            "text": "Type 1 Diabetes: An autoimmune condition where the immune system attacks insulin-producing cells in the pancreas. Symptoms include excessive thirst, frequent urination, hunger, fatigue, and weight loss.",
            "metadata": {
                "name": "Type 1 Diabetes",
                "category": "autoimmune",
                "affected_systems": "pancreas, metabolic",
                "common_tests": "blood glucose, A1C, autoantibody tests"
            }
        },
        {
            "id": "disease_5",
            "text": "Hashimoto's Thyroiditis: An autoimmune disorder affecting the thyroid gland. Symptoms include fatigue, weight gain, cold intolerance, joint and muscle pain, constipation, and depression.",
            "metadata": {
                "name": "Hashimoto's Thyroiditis",
                "category": "autoimmune",
                "affected_systems": "thyroid, metabolic",
                "common_tests": "TSH, T4, anti-TPO antibodies"
            }
        },
        {
            "id": "disease_6",
            "text": "Fibromyalgia: A disorder characterized by widespread musculoskeletal pain accompanied by fatigue, sleep, memory and mood issues. Symptoms include chronic pain throughout the body, fatigue, cognitive difficulties, headaches, and depression.",
            "metadata": {
                "name": "Fibromyalgia",
                "category": "chronic pain",
                "affected_systems": "musculoskeletal, nervous system",
                "common_tests": "tender point examination, exclusion of other conditions"
            }
        },
        {
            "id": "disease_7",
            "text": "Endometriosis: A disorder in which tissue similar to the tissue that normally lines the inside of the uterus grows outside the uterus. Symptoms include painful periods, pain during intercourse, excessive bleeding, and infertility.",
            "metadata": {
                "name": "Endometriosis",
                "category": "inflammatory",
                "affected_systems": "reproductive",
                "common_tests": "laparoscopy, ultrasound, MRI"
            }
        }
    ]
    
    citations = [
        {
            "id": "citation_1",
            "text": "Recent studies have shown that early diagnosis and treatment of autoimmune diseases can significantly improve long-term outcomes and quality of life. (Journal of Autoimmunity, 2023)",
            "metadata": {
                "source": "Journal of Autoimmunity",
                "year": "2023",
                "relevance": "diagnosis"
            }
        },
        {
            "id": "citation_2",
            "text": "Women are more likely than men to develop autoimmune diseases, with hormonal factors playing a significant role in disease onset and progression. (Nature Reviews Immunology, 2022)",
            "metadata": {
                "source": "Nature Reviews Immunology",
                "year": "2022",
                "relevance": "demographics"
            }
        },
        {
            "id": "citation_3",
            "text": "Chronic pain conditions like fibromyalgia are often misdiagnosed, with patients seeing an average of 3.7 different healthcare providers before receiving a correct diagnosis. (Pain Medicine, 2021)",
            "metadata": {
                "source": "Pain Medicine",
                "year": "2021",
                "relevance": "misdiagnosis"
            }
        }
    ]
    
    if disease_collection.count() == 0:
        disease_collection.add(
            ids=[d["id"] for d in diseases],
            documents=[d["text"] for d in diseases],
            metadatas=[d["metadata"] for d in diseases]
        )
        print(f"Added {len(diseases)} diseases to the disease collection")
    else:
        print(f"Disease collection already contains {disease_collection.count()} items")
    
    if citation_collection.count() == 0:
        citation_collection.add(
            ids=[c["id"] for c in citations],
            documents=[c["text"] for c in citations],
            metadatas=[c["metadata"] for c in citations]
        )
        print(f"Added {len(citations)} citations to the citation collection")
    else:
        print(f"Citation collection already contains {citation_collection.count()} items")
    
    print("ChromaDB initialization complete")
    return client

if __name__ == "__main__":
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    initialize_chroma_db(persist_dir)
