from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from models.mongodb.models import JournalEntryCreate, JournalEntry, UserInDB
from models.mongodb.auth import get_current_user
from models.mongodb.database import journal_entries_collection
import openai
import os
from dotenv import load_dotenv
import json

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

router = APIRouter()

@router.post("/journal", response_model=JournalEntry)
async def create_journal_entry(
    entry: JournalEntryCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    """Create a new journal entry with AI analysis"""
    if not entry.date:
        entry.date = datetime.now()
        
    journal_entry = JournalEntry(
        **entry.dict(),
        user_id=current_user.id,
        created_at=datetime.now()
    )
    
    previous_entries = await get_previous_journal_entries(current_user.id)
    
    ai_analysis = await generate_journal_analysis(journal_entry, user=current_user, previous_entries=previous_entries)
    
    journal_entry_dict = journal_entry.dict()
    journal_entry_dict["ai_analysis"] = ai_analysis
    
    await journal_entries_collection.insert_one(journal_entry_dict)
    
    return journal_entry

@router.get("/journal", response_model=List[JournalEntry])
async def get_journal_entries(
    current_user: UserInDB = Depends(get_current_user),
    limit: int = 10,
    skip: int = 0,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get journal entries for the current user"""
    query = {"user_id": current_user.id}
    
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        query["date"] = date_query
    
    entries = await journal_entries_collection.find(query).sort("date", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [JournalEntry(**entry) for entry in entries]

@router.get("/journal/{entry_id}", response_model=JournalEntry)
async def get_journal_entry(
    entry_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get a specific journal entry"""
    entry = await journal_entries_collection.find_one({"id": entry_id, "user_id": current_user.id})
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )
    
    return JournalEntry(**entry)

@router.delete("/journal/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    entry_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Delete a journal entry"""
    result = await journal_entries_collection.delete_one({"id": entry_id, "user_id": current_user.id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )

async def get_previous_journal_entries(user_id: str, limit: int = 20):
    """Get previous journal entries for a user to provide context"""
    entries = await journal_entries_collection.find(
        {"user_id": user_id}
    ).sort("date", -1).limit(limit).to_list(length=limit)
    
    return [JournalEntry(**entry) for entry in entries]

async def format_journal_entry_for_prompt(entry: JournalEntry):
    """Format a journal entry for inclusion in the prompt"""
    symptoms_text = "\n".join([
        f"- {symptom.symptom} (Severity: {symptom.severity}/10)"
        for symptom in entry.symptoms
    ])
    
    env_factors_text = ""
    if entry.environmental_factors:
        env_factors_text = "\n".join([
            f"- {factor.factor_type}: {factor.description}"
            for factor in entry.environmental_factors
        ])
    
    entry_text = f"""
ENTRY DATE: {entry.date.strftime('%Y-%m-%d')}

SYMPTOMS:
{symptoms_text}
"""
    
    if env_factors_text:
        entry_text += f"""
ENVIRONMENTAL FACTORS:
{env_factors_text}
"""
    
    if entry.stress_level:
        entry_text += f"STRESS LEVEL: {entry.stress_level}/10\n"
    
    if entry.diet_notes:
        entry_text += f"DIET NOTES: {entry.diet_notes}\n"
    
    if entry.sleep_quality:
        entry_text += f"SLEEP QUALITY: {entry.sleep_quality}/10\n"
    
    if entry.notes:
        entry_text += f"ADDITIONAL NOTES: {entry.notes}\n"
    
    if hasattr(entry, 'ai_analysis') and entry.ai_analysis:
        analysis = entry.ai_analysis
        
        entry_text += "\nAI ANALYSIS:\n"
        
        if "analysis" in analysis:
            entry_text += f"Analysis: {analysis['analysis']}\n"
        
        if "followUpQuestions" in analysis and analysis["followUpQuestions"]:
            entry_text += "Follow-up Questions:\n"
            for i, question in enumerate(analysis["followUpQuestions"], 1):
                entry_text += f"{i}. {question}\n"
        
        if "trackingSuggestions" in analysis and analysis["trackingSuggestions"]:
            entry_text += "Tracking Suggestions:\n"
            for i, suggestion in enumerate(analysis["trackingSuggestions"], 1):
                entry_text += f"{i}. {suggestion}\n"
        
        if "patternObservations" in analysis and analysis["patternObservations"]:
            entry_text += f"Pattern Observations: {analysis['patternObservations']}\n"
    
    return entry_text

async def generate_journal_analysis(journal_entry: JournalEntry, user: UserInDB, previous_entries: List[JournalEntry] = None):
    """Generate AI analysis and follow-up questions for a journal entry, including previous entries for context"""
    current_entry_text = await format_journal_entry_for_prompt(journal_entry)
    
    previous_entries_text = ""
    if previous_entries:
        previous_entries_text = "PREVIOUS JOURNAL ENTRIES:\n\n"
        for i, entry in enumerate(previous_entries, 1):
            entry_text = await format_journal_entry_for_prompt(entry)
            previous_entries_text += f"--- ENTRY {i} ---\n{entry_text}\n\n"
    
    from vectordb.query_engine import MedicalQueryEngine
    import os
    
    persist_directory = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    query_engine = MedicalQueryEngine(persist_directory)
    
    query_text = journal_entry.notes if journal_entry.notes else ""
    for symptom in journal_entry.symptoms:
        query_text += f" {symptom.symptom}"
    
    all_results = query_engine.query_all_collections(query_text)
    
    rag_context = ""
    if all_results:
        rag_context = "RELEVANT MEDICAL INFORMATION FROM DATABASE:\n\n"
        
        if "disease" in all_results:
            rag_context += "Potential Related Conditions:\n"
            for result in all_results["disease"][:3]:  # Limit to top 3 results
                rag_context += f"- {result['text']}\n"
            rag_context += "\n"
        
        if "autoimmune" in all_results:
            rag_context += "Autoimmune Information:\n"
            for result in all_results["autoimmune"][:3]:  # Limit to top 3 results
                rag_context += f"- {result['text']}\n"
            rag_context += "\n"
        
        if "case" in all_results:
            rag_context += "Similar Case Studies:\n"
            for result in all_results["case"][:3]:  # Limit to top 3 results
                rag_context += f"- {result['text']}\n"
            rag_context += "\n"
    
    prompt = f"""
You are a medical AI assistant analyzing a patient's journal entries for potential autoimmune conditions.

CURRENT JOURNAL ENTRY:
{current_entry_text}

{previous_entries_text}

{rag_context}

Analyze this journal entry to extract and categorize the following:
1. Symptoms (e.g., "feeling tired", "joint pain", "headache")
2. Environmental factors (e.g., "eating gluten", "exposed to allergens", "weather changes")
3. Life stressors (e.g., "boyfriend broke up with me", "work deadline", "financial issues")

Also provide a brief analysis of the symptoms and potential connections to autoimmune conditions.

Format your response as JSON with the following structure:
{{
  "analysis": "Your analysis of the symptoms and potential autoimmune conditions, including follow-up questions",
  "symptoms": [
    "symptom 1",
    "symptom 2",
    ...
  ],
  "environmental_factors": [
    "factor 1",
    "factor 2",
    ...
  ],
  "life_stressors": [
    "stressor 1",
    "stressor 2",
    ...
  ]
}}
"""
    
    model = "gpt-3.5-turbo"
    if user.subscription_tier == "premium":
        model = "gpt-4"
    elif user.subscription_tier == "professional":
        model = "gpt-4-turbo"
    
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
        analysis["timestamp"] = datetime.now().isoformat()
        return analysis
    except Exception as e:
        print(f"Error generating journal analysis: {e}")
        return {
            "analysis": "Unable to generate analysis at this time.",
            "symptoms": [],
            "environmental_factors": [],
            "life_stressors": [],
            "timestamp": datetime.now().isoformat()
        }
