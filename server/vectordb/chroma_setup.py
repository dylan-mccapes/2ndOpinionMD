import os
import sys
import json
from typing import List, Dict, Any, Union
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.normalized_data_processor import process_medical_data_file

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_api_key,
    model_name="text-embedding-3-small"
)

def sanitize_metadata_for_chroma(metadata: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool]]:
    """
    Recursively convert complex types in metadata to strings for ChromaDB compatibility
    
    Args:
        metadata: Dictionary containing metadata with potentially complex types
        
    Returns:
        Dictionary with all values converted to simple types (str, int, float, bool)
    """
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, list):
            sanitized[key] = json.dumps(value)
        elif isinstance(value, dict):
            sanitized[key] = json.dumps(sanitize_metadata_for_chroma(value))
        else:
            sanitized[key] = str(value)
    return sanitized

def setup_chroma_client(persist_directory: str = "./chroma_db"):
    """
    Set up and return a ChromaDB client
    
    Args:
        persist_directory: Directory to persist the ChromaDB data
        
    Returns:
        ChromaDB client
    """
    os.makedirs(persist_directory, exist_ok=True)
    
    client = chromadb.PersistentClient(path=persist_directory)
    
    return client

def create_collections(client, reset: bool = False):
    """
    Create collections in ChromaDB
    
    Args:
        client: ChromaDB client
        reset: Whether to reset existing collections
        
    Returns:
        Dictionary of collections
    """
    collections = {}
    collection_names = ["disease", "case", "condition", "autoimmune", "patient", "citation"]
    
    for name in collection_names:
        if reset and name in [col.name for col in client.list_collections()]:
            client.delete_collection(name)
        
        collections[name] = client.get_or_create_collection(
            name=name,
            embedding_function=openai_ef,
            metadata={"description": f"Medical {name} data"}
        )
    
    return collections

def add_data_to_collections(collections, processed_data):
    """
    Add data to ChromaDB collections
    
    Args:
        collections: Dictionary of ChromaDB collections
        processed_data: List of processed data entries
    """
    data_by_type = {}
    for item in processed_data:
        item_type = item.get('type', 'unknown')
        if item_type not in data_by_type:
            data_by_type[item_type] = []
        data_by_type[item_type].append(item)
    
    # Add data to collections
    for data_type, items in data_by_type.items():
        if data_type in collections:
            collections[data_type].add(
                ids=[item["id"] for item in items],
                documents=[item["text"] for item in items],
                metadatas=[sanitize_metadata_for_chroma(item["metadata"]) for item in items]
            )
            print(f"Added {len(items)} {data_type} entries to ChromaDB")

def main(json_file_path: str, persist_directory: str = "./chroma_db", reset: bool = False):
    """
    Main function to set up ChromaDB and add data
    
    Args:
        json_file_path: Path to the JSON file containing medical data
        persist_directory: Directory to persist the ChromaDB data
        reset: Whether to reset existing collections
    """
    processed_data = process_medical_data_file(json_file_path)
    if not processed_data:
        print("No data processed. Exiting.")
        return
    
    client = setup_chroma_client(persist_directory)
    collections = create_collections(client, reset)
    
    # Add data to collections
    add_data_to_collections(collections, processed_data)
    
    print("ChromaDB setup complete!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Set up ChromaDB with medical data")
    parser.add_argument("json_file", help="Path to the JSON file containing medical data")
    parser.add_argument("--persist-dir", default="./chroma_db", help="Directory to persist the ChromaDB data")
    parser.add_argument("--reset", action="store_true", help="Reset existing collections")
    
    args = parser.parse_args()
    
    main(args.json_file, args.persist_dir, args.reset)
