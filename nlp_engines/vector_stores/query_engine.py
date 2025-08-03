import os
import sys
import json
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import openai
import logging

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.warning("OPENAI_API_KEY environment variable not set. Using placeholder for demo.")
    openai_api_key = "sk-placeholder"

openai.api_key = openai_api_key

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_api_key,
    model_name="text-embedding-3-small"
)

class MedicalQueryEngine:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize the medical query engine
        
        Args:
            persist_directory: Directory where ChromaDB data is persisted
        """
        os.makedirs(persist_directory, exist_ok=True)
        
        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
            
            self.collections = {}
            for collection_info in self.client.list_collections():
                collection_name = collection_info.name
                self.collections[collection_name] = self.client.get_collection(
                    name=collection_name,
                    embedding_function=openai_ef
                )
            
            if not self.collections:
                logger.info("No collections found. Creating default collections.")
                self.collections["disease"] = self.client.get_or_create_collection(
                    name="disease",
                    embedding_function=openai_ef
                )
                
                self.collections["citation"] = self.client.get_or_create_collection(
                    name="citation",
                    embedding_function=openai_ef
                )
                
                from vectordb.initialize_db import initialize_chroma_db
                initialize_chroma_db(persist_directory)
                
                self.collections = {}
                for collection_info in self.client.list_collections():
                    collection_name = collection_info.name
                    self.collections[collection_name] = self.client.get_collection(
                        name=collection_name,
                        embedding_function=openai_ef
                    )
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            self.collections = {
                "disease": None,
                "citation": None
            }
    
    def query_collection(self, collection_name: str, query: str, top_k: int = 5):
        """
        Query a specific collection
        
        Args:
            collection_name: Name of the collection to query
            query: Query string
            top_k: Number of top results to return
            
        Returns:
            List of results with metadata
        """
        if collection_name not in self.collections or self.collections[collection_name] is None:
            logger.warning(f"Collection '{collection_name}' not found or not initialized")
            return []
        
        try:
            results = self.collections[collection_name].query(
                query_texts=[query],
                n_results=top_k
            )
            
            formatted_results = []
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if "distances" in results else 0
                
                similarity = 1 - min(distance, 1.0)  # Ensure similarity is between 0 and 1
                confidence = int(similarity * 100)
                
                result = {
                    "id": doc_id,
                    "confidence": confidence,
                    "text": results["documents"][0][i],
                    "metadata": metadata
                }
                
                formatted_results.append(result)
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error querying collection '{collection_name}': {e}")
            return []
    
    def query_all_collections(self, query: str, top_k: int = 3):
        """
        Query all collections
        
        Args:
            query: Query string
            top_k: Number of top results to return per collection
            
        Returns:
            Dictionary of results by collection
        """
        results = {}
        
        for collection_name in self.collections:
            collection_results = self.query_collection(collection_name, query, top_k)
            if collection_results:
                results[collection_name] = collection_results
        
        return results
    
    def generate_rag_response(self, symptoms: List[str], model: str = "gpt-3.5-turbo", demographics: Dict[str, Any] = None):
        """
        Generate a RAG response using all available collections
        
        Args:
            symptoms: List of symptom strings
            model: LLM model to use
            demographics: Optional dictionary containing patient demographics
            
        Returns:
            Dictionary containing the RAG response
        """
        logger.info(f"Generating RAG response with model: {model}")
        logger.info(f"Symptoms: {symptoms}")
        logger.info(f"Demographics: {demographics}")
        
        if not symptoms or not isinstance(symptoms, list):
            logger.error(f"Invalid symptoms format: {symptoms}")
            return {
                "diagnoses": [
                    {
                        "name": "Input Error",
                        "confidence": 0,
                        "explanation": "Invalid symptoms format. Please provide a list of symptom strings.",
                        "redFlags": [],
                        "labSuggestions": []
                    }
                ]
            }
        
        query_text = f"Patient symptoms: {', '.join(symptoms)}"
        
        if demographics:
            try:
                demo_text = ", ".join([f"{k}: {v}" for k, v in demographics.items()])
                query_text += f"\nPatient demographics: {demo_text}"
            except Exception as e:
                logger.error(f"Error formatting demographics: {e}")
        
        all_results = self.query_all_collections(query_text)
        
        context = ""
        
        if "disease" in all_results:
            context += "Potential Diagnoses:\n\n"
            for result in all_results["disease"]:
                context += f"Diagnosis (Confidence: {result['confidence']}%):\n"
                context += f"{result['text']}\n\n"
        
        if "case" in all_results:
            context += "Relevant Case Studies:\n\n"
            for result in all_results["case"]:
                context += f"Case Study (Confidence: {result['confidence']}%):\n"
                context += f"{result['text']}\n\n"
        
        if "condition" in all_results:
            context += "Relevant Conditions:\n\n"
            for result in all_results["condition"]:
                context += f"Condition (Confidence: {result['confidence']}%):\n"
                context += f"{result['text']}\n\n"
        
        if "citation" in all_results:
            context += "Relevant Citations:\n\n"
            for result in all_results["citation"]:
                context += f"Citation (Confidence: {result['confidence']}%):\n"
                context += f"{result['text']}\n\n"
        
        if "autoimmune" in all_results:
            context += "Relevant Autoimmune Information:\n\n"
            for result in all_results["autoimmune"]:
                context += f"Autoimmune (Confidence: {result['confidence']}%):\n"
                context += f"{result['text']}\n\n"
        
        if "patient" in all_results:
            context += "Similar Patient Profiles:\n\n"
            for result in all_results["patient"]:
                context += f"Patient (Confidence: {result['confidence']}%):\n"
                context += f"{result['text']}\n\n"
        
        if not context:
            logger.warning("No relevant context found in vector database")
            return {
                "diagnoses": [
                    {
                        "name": "Insufficient Data",
                        "confidence": 0,
                        "explanation": "Unable to find relevant medical information for the provided symptoms. Please provide more detailed symptoms.",
                        "redFlags": [],
                        "labSuggestions": ["Complete blood count", "Comprehensive metabolic panel"]
                    }
                ]
            }
        
        demographics_str = ""
        if demographics:
            demographics_str = "Patient demographics:\n"
            for key, value in demographics.items():
                demographics_str += f"- {key}: {value}\n"
        
        prompt = f"""
        You are a medical AI assistant helping analyze potential autoimmune diagnoses.
        
        Patient symptoms: {', '.join(symptoms)}
        {demographics_str}
        Based on vector similarity search, these conditions and research might be relevant:
        
        {context}
        
        Please analyze these potential diagnoses in relation to the patient's symptoms and demographics.
        For each condition, explain why it might be relevant and provide a confidence score.
        Include important red flags to watch for and suggested lab tests.
        Format your response as JSON with the following structure:
        {{
          "diagnoses": [
            {{
              "name": "Condition Name",
              "confidence": 85,
              "explanation": "Why this condition matches the symptoms",
              "redFlags": ["Red flag 1", "Red flag 2"],
              "labSuggestions": ["Test 1", "Test 2"]
            }}
          ]
        }}
        """
        
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a medical AI assistant specializing in autoimmune diseases."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message['content']
            
            if content.startswith("```json") or content.startswith("```"):
                start_idx = content.find("\n") + 1
                end_idx = content.rfind("```")
                
                if end_idx > start_idx:
                    content = content[start_idx:end_idx].strip()
                else:
                    content = content[start_idx:].strip()
            
            analysis = json.loads(content)
            return analysis
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            if 'response' in locals():
                logger.error(f"Response content: {response.choices[0].message['content']}")
            
            return {
                "diagnoses": [
                    {
                        "name": "Analysis Error",
                        "confidence": 0,
                        "explanation": "Unable to generate structured analysis. Please try again with different symptoms.",
                        "redFlags": [],
                        "labSuggestions": []
                    }
                ]
            }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Query the medical database")
    parser.add_argument("--symptoms", nargs="+", required=True, help="List of symptoms")
    parser.add_argument("--persist-dir", default="./chroma_db", help="Directory where ChromaDB data is persisted")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="LLM model to use")
    
    args = parser.parse_args()
    
    engine = MedicalQueryEngine(args.persist_dir)
    response = engine.generate_rag_response(args.symptoms, args.model)
    
    print(json.dumps(response, indent=2))
