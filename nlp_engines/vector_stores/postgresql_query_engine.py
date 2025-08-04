import os
import openai
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.postgresql.database import async_session
from database.models.postgresql.models import MedicalKnowledge
from dotenv import load_dotenv
import logging

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)
openai.api_key = os.getenv("OPENAI_API_KEY")
logger = logging.getLogger(__name__)

class PostgreSQLMedicalQueryEngine:
    def __init__(self):
        pass

    async def get_embedding(self, text: str):
        try:
            response = await openai.Embedding.acreate(
                model="text-embedding-3-small",
                input=text
            )
            return response['data'][0]['embedding']
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Using dummy embedding for testing.")
            import numpy as np
            return np.random.random(1536).tolist()

    async def query_medical_knowledge(self, query: str, content_types: Optional[List[str]] = None, top_k: int = 5):
        query_embedding = await self.get_embedding(query)
        
        async with async_session() as session:
            if isinstance(query_embedding, list):
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            else:
                embedding_str = str(query_embedding)
            
            limit = top_k * 3 if content_types else top_k
            
            sql = f"""
            SELECT id, content_type, title, content, icd10_code, meta_data,
                   embedding <-> '{embedding_str}'::vector as distance
            FROM medical_knowledge
            ORDER BY embedding <-> '{embedding_str}'::vector 
            LIMIT {limit}
            """
            
            result = await session.execute(text(sql))
            rows = result.fetchall()
            
            formatted_results = []
            for row in rows:
                if content_types and row.content_type not in content_types:
                    continue
                    
                similarity = 1 - min(row.distance, 1.0)
                confidence = int(similarity * 100)
                
                formatted_results.append({
                    "id": str(row.id),
                    "confidence": confidence,
                    "text": row.content,
                    "content_type": row.content_type,
                    "title": row.title,
                    "icd10_code": row.icd10_code,
                    "metadata": row.meta_data
                })
                
                if len(formatted_results) >= top_k:
                    break
            
            return formatted_results

    async def query_all_collections(self, query_text: str, top_k: int = 3):
        """Query all collections and return results grouped by content type"""
        if not query_text or query_text.strip() == "":
            return {}
            
        results = await self.query_medical_knowledge(query_text, top_k=top_k*3)
        
        grouped_results = {}
        for result in results:
            content_type = result["content_type"]
            if content_type not in grouped_results:
                grouped_results[content_type] = []
            grouped_results[content_type].append(result)
            
            if len(grouped_results[content_type]) > top_k:
                grouped_results[content_type] = grouped_results[content_type][:top_k]
        
        return grouped_results

    async def generate_rag_response(self, symptoms: List[str], model: str = "gpt-3.5-turbo", demographics: Optional[Dict[str, Any]] = None):
        query_text = f"Patient symptoms: {', '.join(symptoms)}"
        
        if demographics:
            demo_text = ", ".join([f"{k}: {v}" for k, v in demographics.items()])
            query_text += f"\nPatient demographics: {demo_text}"
        
        disease_results = await self.query_medical_knowledge(query_text, ["icd10_condition", "disease"], 3)
        case_results = await self.query_medical_knowledge(query_text, ["case"], 3)
        drug_results = await self.query_medical_knowledge(query_text, ["icd10_drug"], 3)
        
        context = ""
        if disease_results:
            context += "Relevant ICD-10 Conditions and Diseases:\n\n"
            for result in disease_results:
                context += f"- {result['title']} (ICD-10: {result.get('icd10_code', 'N/A')}) - Confidence: {result['confidence']}%\n"
                context += f"  {result['text']}\n\n"
        
        if case_results:
            context += "Relevant Case Studies:\n\n"
            for result in case_results:
                context += f"- {result['title']} - Confidence: {result['confidence']}%\n"
                context += f"  {result['text']}\n\n"
                
        if drug_results:
            context += "Relevant Medications:\n\n"
            for result in drug_results:
                context += f"- {result['title']} (ICD-10: {result.get('icd10_code', 'N/A')}) - Confidence: {result['confidence']}%\n"
                context += f"  {result['text']}\n\n"
        
        prompt = f"""
        You are a medical AI assistant analyzing symptoms with access to ICD-10 diagnostic codes.
        
        Patient symptoms: {', '.join(symptoms)}
        {f"Patient demographics: {demographics}" if demographics else ""}
        
        Based on ICD-10 and medical knowledge:
        {context}
        
        Provide diagnostic analysis with ICD-10 codes where applicable.
        Format as JSON with diagnoses, confidence scores, ICD-10 codes, and recommendations.
        """
        
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=[
                {"role": "system", "content": "You are a medical AI assistant specializing in ICD-10 diagnostic coding."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message['content']
