from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import re

from models.mongodb.models import JournalEntryCreate, JournalEntry, UserInDB
from models.mongodb.auth import get_current_user
from models.mongodb.database import journal_entries_collection, reports_collection
import openai
import os
from dotenv import load_dotenv
import json

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

ZONES = {
    1: "Zone 1 - Stable Terrain",
    2: "Zone 2 - Mild Fluctuation",
    3: "Zone 3 - Moderate Instability",
    4: "Zone 4 - Flare-Dominant State",
    5: "Zone 5 - Collapsed Capacity"
}

STAX_LEVELS = {
    1: "STAX 1 - Single-diagnosis threshold",
    2: "STAX 2 - Multi-diagnosis state",
    3: "STAX 3 - Multisystem failure",
    4: "STAX 4 - Complex collapse"
}

def generate_ethos_prompt():
    """Generate a prompt based on the ethos of health model"""
    return """
Using the 2OPMD Diagnostic Terrain System:
- Consider Nucleus State of Health and Parallel-Adjusted Nucleus State (PANS)
- Assess STAX levels (Z-Axis progression) for disease complexity
- Evaluate patient stability using Zones 1-5
- Identify Early Zone Shifts, Epigenetic Echoes, and Overshoot patterns
- Detect Somatic Healing Threshold Responses and potential Safe Pause needs
- Consider misdiagnosis patterns and tags
"""

router = APIRouter()

@router.post("/journal", response_model=JournalEntry)
async def create_journal_entry(
    entry: JournalEntryCreate,
    current_user: UserInDB = Depends(get_current_user),
    report_id: Optional[str] = None
):
    """Create a new journal entry with AI analysis using the ethos of health model"""
    if not entry.date:
        entry.date = datetime.now()

    journal_entry = JournalEntry(
        **entry.dict(),
        user_id=current_user.id,
        created_at=datetime.now()
    )

    previous_entries = await get_previous_journal_entries(current_user.id)

    previous_diagnoses = []
    report = None
    if report_id:
        report = await reports_collection.find_one({"id": report_id, "userId": current_user.id})
        if report and "diagnosticResults" in report:
            previous_diagnoses = report["diagnosticResults"]

    ai_analysis = await generate_journal_analysis(
        journal_entry,
        user=current_user,
        previous_entries=previous_entries,
        previous_diagnoses=previous_diagnoses
    )

    journal_entry_dict = journal_entry.dict()
    journal_entry_dict["ai_analysis"] = ai_analysis

    result = await journal_entries_collection.insert_one(journal_entry_dict)

    if report_id and report and "diagnoses" in ai_analysis:
        updated_diagnoses = []

        existing_diagnoses_map = {}
        for diagnosis in report["diagnosticResults"]:
            existing_diagnoses_map[diagnosis["name"]] = diagnosis

        for diagnosis in ai_analysis["diagnoses"]:
            if diagnosis["status"] == "eliminated":
                continue
            elif diagnosis["status"] == "new":
                if "staxLevel" not in diagnosis:
                    diagnosis["staxLevel"] = 1
                if "zone" not in diagnosis:
                    diagnosis["zone"] = 1
                if "tags" not in diagnosis:
                    diagnosis["tags"] = []
                updated_diagnoses.append(diagnosis)
            elif diagnosis["name"] in existing_diagnoses_map:
                existing_diagnosis = existing_diagnoses_map[diagnosis["name"]]
                updated_diagnoses.append({
                    **existing_diagnosis,
                    "confidence": diagnosis["confidence"],
                    "staxLevel": diagnosis.get("staxLevel", existing_diagnosis.get("staxLevel", 1)),
                    "zone": diagnosis.get("zone", existing_diagnosis.get("zone", 1)),
                    "tags": diagnosis.get("tags", existing_diagnosis.get("tags", [])),
                    "status": diagnosis["status"]
                })

        for diagnosis in report["diagnosticResults"]:
            if not any(d["name"] == diagnosis["name"] for d in updated_diagnoses):
                updated_diagnoses.append(diagnosis)

        await reports_collection.update_one(
            {"id": report_id},
            {"$set": {
                "diagnosticResults": updated_diagnoses,
                "updatedAt": datetime.now()
            }}
        )

        await reports_collection.update_one(
            {"id": report_id},
            {"$push": {
                "journalEntries": {
                    "entryDate": entry.date,
                    "content": entry.notes,
                    "analysis": {
                        "symptoms": ai_analysis.get("symptoms", []),
                        "environmentalFactors": ai_analysis.get("environmental_factors", []),
                        "lifeStressors": ai_analysis.get("life_stressors", []),
                        "diagnoses": ai_analysis.get("diagnoses", [])
                    },
                    "journalingRecommendation": ai_analysis.get("journalingRecommendation", None)
                }
            }}
        )

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

@router.get("/timeline/{report_id}")
async def get_timeline_data(
    report_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get timeline data for a specific report including initial diagnosis and all journal entries"""
    # Get the report for initial diagnosis
    report = await reports_collection.find_one({"id": report_id, "userId": current_user.id})
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    journal_entries = await journal_entries_collection.find(
        {"reportId": report_id, "user_id": current_user.id}
    ).sort("date", 1).to_list(length=100)  # Sort chronologically
    
    timeline_data = {
        "initialDiagnosis": {
            "date": report.get("createdAt", datetime.now()),
            "diagnoses": report.get("diagnosticResults", [])
        },
        "journalEntries": journal_entries
    }
    
    return timeline_data

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

async def format_journal_entry_for_prompt(entry: JournalEntry, include_ethos: bool = True):
    """Format a journal entry for inclusion in the prompt with ethos of health model"""
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

    parsed_sentences = []
    if entry.notes:
        raw_sentences = re.split(r'[.,!?;]+', entry.notes)
        parsed_sentences = [s.strip() for s in raw_sentences if s.strip()]

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

        if parsed_sentences:
            entry_text += "\nPARSED SENTENCES:\n"
            for i, sentence in enumerate(parsed_sentences, 1):
                entry_text += f"{i}. {sentence}\n"

    if hasattr(entry, 'ai_analysis') and entry.ai_analysis:
        analysis = entry.ai_analysis

        entry_text += "\nAI ANALYSIS:\n"

        if "analysis" in analysis:
            entry_text += f"Analysis: {analysis['analysis']}\n"

        if "diagnoses" in analysis and analysis["diagnoses"]:
            entry_text += "Diagnoses:\n"
            for i, diagnosis in enumerate(analysis["diagnoses"], 1):
                status_text = ""
                if "status" in diagnosis:
                    status_text = f" ({diagnosis['status'].upper()})"

                entry_text += f"{i}. {diagnosis['name']}{status_text} - Confidence: {diagnosis['confidence']}%\n"

                if "staxLevel" in diagnosis:
                    stax_desc = STAX_LEVELS.get(diagnosis['staxLevel'], f"STAX {diagnosis['staxLevel']}")
                    entry_text += f"   STAX Level: {stax_desc}\n"

                if "zone" in diagnosis:
                    zone_desc = ZONES.get(diagnosis['zone'], f"Zone {diagnosis['zone']}")
                    entry_text += f"   Zone: {zone_desc}\n"

                if "tags" in diagnosis and diagnosis["tags"]:
                    entry_text += f"   Tags: {', '.join(diagnosis['tags'])}\n"

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

        if "journalingRecommendation" in analysis and analysis["journalingRecommendation"]:
            entry_text += "Journaling Recommendation:\n"
            entry_text += f"Type: {analysis['journalingRecommendation']['promptType']}\n"
            entry_text += f"Prompt: {analysis['journalingRecommendation']['suggestedPrompt']}\n"

    return entry_text

async def generate_journal_analysis(
    journal_entry: JournalEntry,
    user: UserInDB,
    previous_entries: List[JournalEntry] = None,
    previous_diagnoses: List[Dict[str, Any]] = None
):
    """Generate AI analysis and follow-up questions for a journal entry using the ethos of health model"""
    current_entry_text = await format_journal_entry_for_prompt(journal_entry, include_ethos=True)

    parsed_sentences = []
    if journal_entry.notes:
        raw_sentences = re.split(r'[.,!?;]+', journal_entry.notes)
        parsed_sentences = [s.strip() for s in raw_sentences if s.strip()]

    previous_entries_text = ""
    if previous_entries:
        previous_entries_text = "PREVIOUS JOURNAL ENTRIES:\n\n"
        for i, entry in enumerate(previous_entries, 1):
            entry_text = await format_journal_entry_for_prompt(entry)
            previous_entries_text += f"--- ENTRY {i} ---\n{entry_text}\n\n"

    ethos_prompt = generate_ethos_prompt()

    previous_diagnoses_text = ""
    if previous_diagnoses:
        previous_diagnoses_text = "PREVIOUS DIAGNOSES:\n"
        for i, diagnosis in enumerate(previous_diagnoses, 1):
            confidence = diagnosis.get("confidence", 0)
            stax_level = diagnosis.get("staxLevel", 1)
            zone = diagnosis.get("zone", 1)
            tags = diagnosis.get("tags", [])

            previous_diagnoses_text += f"{i}. {diagnosis['name']} - Confidence: {confidence}%\n"
            previous_diagnoses_text += f"   STAX Level: {stax_level}, Zone: {zone}\n"
            if tags:
                previous_diagnoses_text += f"   Tags: {', '.join(tags)}\n"

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
You are a medical AI assistant analyzing a patient's journal entries using the 2OPMD Diagnostic Terrain System.

{ethos_prompt}

CURRENT JOURNAL ENTRY:
{current_entry_text}

PARSED SENTENCES:
{chr(10).join([f"{i+1}. {sentence}" for i, sentence in enumerate(parsed_sentences)])}

{previous_diagnoses_text}

{previous_entries_text}

{rag_context}

Analyze this journal entry to extract and categorize the following:
1. Symptoms (e.g., "feeling tired", "joint pain", "headache")
2. Environmental factors (e.g., "eating gluten", "exposed to allergens", "weather changes")
3. Life stressors (e.g., "boyfriend broke up with me", "work deadline", "financial issues")

For each individual sentence in the parsed sentences list, determine whether it contains:
- Symptoms: Physical or mental health issues experienced by the patient
- Environmental factors: External elements that might affect health (diet, allergens, etc.)
- Life stressors: Personal events or situations causing stress or emotional impact

Then, based on this analysis:
- Confirm or adjust confidence in existing diagnoses
- Suggest new potential diagnoses if indicated
- Identify any diagnoses that should be eliminated
- Assign appropriate STAX levels and Zone classifications based on symptom severity, complexity, and stability
  - STAX levels (1-4): Higher levels indicate more complex, layered conditions
  - Zones (1-5): Higher numbers indicate less stability and more frequent/severe symptoms
- Apply relevant clinical and symbolic tags

Format your response as JSON with the following structure:
{{
  "analysis": "Your analysis of the symptoms and potential autoimmune conditions",
  "symptoms": [
    "symptom 1",
    "symptom 2"
  ],
  "environmental_factors": [
    "factor 1",
    "factor 2"
  ],
  "life_stressors": [
    "stressor 1",
    "stressor 2"
  ],
  "diagnoses": [
    {{
      "name": "Diagnosis name",
      "confidence": 85,
      "status": "confirmed/new/eliminated",
      "staxLevel": 1,
      "zone": 2,
      "tags": ["#SuspectedDx_DiagnosisName", "#EarlyZoneShift"]
    }}
  ],
  "journalingRecommendation": {{
    "promptType": "Clinical/Somatic/Symbolic/Remission",
    "suggestedPrompt": "What was lost when health left?"
  }},
  "followUpQuestions": [
    "question 1",
    "question 2"
  ],
  "trackingSuggestions": [
    "suggestion 1",
    "suggestion 2"
  ],
  "patternObservations": "Any patterns observed across journal entries"
}}
"""

    model = "gpt-4-turbo"  # Use gpt-4-turbo for all users for better analysis
    if user.subscription_tier == "premium":
        model = "gpt-4-turbo"
    elif user.subscription_tier == "professional":
        model = "gpt-4-turbo"

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a medical AI assistant specializing in autoimmune diseases and the 2OPMD Diagnostic Terrain System."},
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

        if "diagnoses" in analysis:
            for diagnosis in analysis["diagnoses"]:
                if "staxLevel" not in diagnosis:
                    diagnosis["staxLevel"] = 1
                if "zone" not in diagnosis:
                    diagnosis["zone"] = 1
                if "tags" not in diagnosis:
                    diagnosis["tags"] = []
                if "status" not in diagnosis:
                    diagnosis["status"] = "confirmed"

        return analysis
    except Exception as e:
        print(f"Error generating journal analysis: {e}")
        return {
            "analysis": "Unable to generate analysis at this time.",
            "symptoms": [],
            "environmental_factors": [],
            "life_stressors": [],
            "diagnoses": [],
            "journalingRecommendation": {
                "promptType": "Clinical",
                "suggestedPrompt": "Please describe your symptoms in detail."
            },
            "timestamp": datetime.now().isoformat()
        }
