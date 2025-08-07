from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import re
import asyncio

from database.models.postgresql.models import JournalEntry, User
from server.api.auth_postgres import get_current_user_postgres as get_current_user
from database.models.postgresql.database import get_db
from pydantic import BaseModel, Field
from typing import Optional

class SymptomEntry(BaseModel):
    symptom: str
    severity: int = Field(ge=1, le=10)

class EnvironmentalFactor(BaseModel):
    factor_type: str
    description: str

class JournalEntryCreate(BaseModel):
    symptoms: Optional[list] = None
    environmental_factors: Optional[list] = None
    stress_level: Optional[int] = None
    diet_notes: Optional[str] = None
    sleep_quality: Optional[int] = None
    notes: Optional[str] = None

class JournalEntryResponse(BaseModel):
    id: str
    user_id: str
    date: datetime
    symptoms: Optional[list] = None
    environmental_factors: Optional[list] = None
    stress_level: Optional[int] = None
    diet_notes: Optional[str] = None
    sleep_quality: Optional[int] = None
    notes: Optional[str] = None
    analysis: Optional[str] = None
    pattern_observations: Optional[str] = None
    ai_analysis: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
import openai
import os
from dotenv import load_dotenv
import json

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

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

@router.post("/journal", response_model=JournalEntryResponse)
async def create_journal_entry(
    entry: JournalEntryCreate,
    current_user: User = Depends(get_current_user),
    report_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
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
    symptom_intake_data = {}

    ai_analysis = await generate_journal_analysis(
        journal_entry,
        user=current_user,
        previous_entries=previous_entries,
        previous_diagnoses=previous_diagnoses,
        symptom_intake_data=symptom_intake_data
    )

    journal_entry_dict = journal_entry.dict()
    journal_entry_dict["ai_analysis"] = ai_analysis
    
    if "symptoms" in ai_analysis and ai_analysis["symptoms"]:
        structured_symptoms = []
        for symptom in ai_analysis["symptoms"]:
            if isinstance(symptom, str):
                structured_symptoms.append({
                    "symptom": symptom,
                    "severity": 5  # Default severity for AI-extracted symptoms
                })
            elif isinstance(symptom, dict) and "symptom" in symptom:
                structured_symptoms.append(symptom)
        
        if structured_symptoms:
            journal_entry_dict["symptoms"] = structured_symptoms
            print(f"\n=== REPLACED RAW SYMPTOMS WITH AI-EXTRACTED ===")
            print(f"Original symptoms count: {len(journal_entry.symptoms)}")
            print(f"AI-extracted symptoms count: {len(structured_symptoms)}")
            for i, symptom in enumerate(structured_symptoms):
                print(f"  {i+1}. {symptom['symptom']} (Severity: {symptom['severity']}/10)")
    
    print("\n=== JOURNAL ANALYSIS RESULTS ===")
    print(json.dumps(ai_analysis, indent=2))
    
    print("\n=== CATEGORIZED DATA SUMMARY ===")
    print(f"Symptoms: {len(ai_analysis.get('symptoms', []))} items")
    print(f"Environmental factors: {len(ai_analysis.get('environmental_factors', []))} items")
    print(f"Life stressors: {len(ai_analysis.get('life_stressors', []))} items")
    print(f"Diagnoses: {len(ai_analysis.get('diagnoses', []))} items")
    
    if 'analysis' in ai_analysis:
        print("\n=== ANALYSIS TEXT ===")
        print(ai_analysis['analysis'])
    
    db_entry = JournalEntry(
        user_id=current_user.id,
        date=entry.date,
        symptoms=[symptom.dict() for symptom in entry.symptoms],
        environmental_factors=[factor.dict() for factor in entry.environmental_factors] if entry.environmental_factors else [],
        stress_level=entry.stress_level,
        diet_notes=entry.diet_notes,
        sleep_quality=entry.sleep_quality,
        notes=entry.notes,
        analysis=entry.analysis,
        pattern_observations=entry.patternObservations,
        ai_analysis=ai_analysis,
        created_at=datetime.now()
    )
    
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)

    return journal_entry

@router.get("/journal", response_model=List[JournalEntryResponse])
async def get_journal_entries(
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    skip: int = 0,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get journal entries for the current user"""
    query = select(JournalEntry).where(JournalEntry.user_id == current_user.id)
    
    if start_date:
        query = query.where(JournalEntry.date >= start_date)
    if end_date:
        query = query.where(JournalEntry.date <= end_date)
        
    query = query.order_by(JournalEntry.date.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    db_entries = result.scalars().all()
    
    entries = []
    for db_entry in db_entries:
        entries.append(JournalEntry(
            id=str(db_entry.id),
            user_id=str(db_entry.user_id),
            date=db_entry.date,
            symptoms=[SymptomEntry(**symptom) for symptom in db_entry.symptoms],
            environmental_factors=[EnvironmentalFactor(**factor) for factor in db_entry.environmental_factors] if db_entry.environmental_factors else [],
            stress_level=db_entry.stress_level,
            diet_notes=db_entry.diet_notes,
            sleep_quality=db_entry.sleep_quality,
            notes=db_entry.notes,
            analysis=db_entry.analysis,
            patternObservations=db_entry.pattern_observations,
            ai_analysis=db_entry.ai_analysis,
            created_at=db_entry.created_at,
            updated_at=db_entry.updated_at
        ))
    
    return entries

@router.get("/journal/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific journal entry"""
    query = select(JournalEntry).where(
        and_(JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id)
    )
    result = await db.execute(query)
    db_entry = result.scalar_one_or_none()
    
    if db_entry:
        return JournalEntry(
            id=str(db_entry.id),
            user_id=str(db_entry.user_id),
            date=db_entry.date,
            symptoms=[SymptomEntry(**symptom) for symptom in db_entry.symptoms],
            environmental_factors=[EnvironmentalFactor(**factor) for factor in db_entry.environmental_factors] if db_entry.environmental_factors else [],
            stress_level=db_entry.stress_level,
            diet_notes=db_entry.diet_notes,
            sleep_quality=db_entry.sleep_quality,
            notes=db_entry.notes,
            analysis=db_entry.analysis,
            patternObservations=db_entry.pattern_observations,
            ai_analysis=db_entry.ai_analysis,
            created_at=db_entry.created_at,
            updated_at=db_entry.updated_at
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Journal entry not found"
    )

@router.get("/timeline/{report_id}")
async def get_timeline_data(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get timeline data for a specific report including initial diagnosis and all journal entries"""
    query = select(JournalEntry).where(JournalEntry.user_id == current_user.id).order_by(JournalEntry.date.asc())
    result = await db.execute(query)
    db_entries = result.scalars().all()
    
    journal_entries = []
    for db_entry in db_entries:
        journal_entries.append({
            "id": str(db_entry.id),
            "user_id": str(db_entry.user_id),
            "date": db_entry.date,
            "symptoms": db_entry.symptoms,
            "environmental_factors": db_entry.environmental_factors,
            "stress_level": db_entry.stress_level,
            "diet_notes": db_entry.diet_notes,
            "sleep_quality": db_entry.sleep_quality,
            "notes": db_entry.notes,
            "analysis": db_entry.analysis,
            "pattern_observations": db_entry.pattern_observations,
            "ai_analysis": db_entry.ai_analysis,
            "created_at": db_entry.created_at,
            "updated_at": db_entry.updated_at
        })
    
    timeline_data = {
        "initialDiagnosis": {
            "date": datetime.now(),
            "diagnoses": []
        },
        "journalEntries": journal_entries
    }
    
    return timeline_data

@router.delete("/journal/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a journal entry"""
    query = select(JournalEntry).where(
        and_(JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id)
    )
    result = await db.execute(query)
    db_entry = result.scalar_one_or_none()
    
    if db_entry:
        await db.delete(db_entry)
        await db.commit()
        return

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Journal entry not found"
    )

async def get_previous_journal_entries(user_id: str, limit: int = 20, db: AsyncSession = None):
    """Get previous journal entries for a user to provide context"""
    
    if not db:
        return []
    
    from database.models.postgresql.models import JournalEntry as JournalEntry
    query = select(JournalEntry).where(JournalEntry.user_id == user_id).order_by(JournalEntry.date.desc()).limit(limit)
    result = await db.execute(query)
    db_entries = result.scalars().all()
    
    entries = []
    for db_entry in db_entries:
        entries.append(JournalEntry(
            id=str(db_entry.id),
            user_id=str(db_entry.user_id),
            date=db_entry.date,
            symptoms=[SymptomEntry(**symptom) for symptom in db_entry.symptoms] if db_entry.symptoms else [],
            environmental_factors=[EnvironmentalFactor(**factor) for factor in db_entry.environmental_factors] if db_entry.environmental_factors else [],
            stress_level=db_entry.stress_level,
            diet_notes=db_entry.diet_notes,
            sleep_quality=db_entry.sleep_quality,
            notes=db_entry.notes,
            analysis=db_entry.analysis,
            patternObservations=db_entry.pattern_observations,
            ai_analysis=db_entry.ai_analysis,
            created_at=db_entry.created_at,
            updated_at=db_entry.updated_at
        ))
    return entries

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
    user: User,
    previous_entries: List[JournalEntry] = [],
    previous_diagnoses: List[Dict[str, Any]] = [],
    symptom_intake_data: Dict[str, Any] = {},
    query_engine = None
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

    symptom_intake_context = ""
    if symptom_intake_data:
        symptom_intake_context = "INITIAL SYMPTOM INTAKE DATA:\n"
        if symptom_intake_data.get("intake_timestamp"):
            symptom_intake_context += f"Intake Date: {symptom_intake_data['intake_timestamp']}\n"
        if symptom_intake_data.get("age"):
            symptom_intake_context += f"Age: {symptom_intake_data['age']}\n"
        if symptom_intake_data.get("birthdate"):
            symptom_intake_context += f"Birthdate: {symptom_intake_data['birthdate']}\n"
        if symptom_intake_data.get("sex"):
            symptom_intake_context += f"Sex: {symptom_intake_data['sex']}\n"
        if symptom_intake_data.get("height"):
            symptom_intake_context += f"Height: {symptom_intake_data['height']}\n"
        if symptom_intake_data.get("weight"):
            symptom_intake_context += f"Weight: {symptom_intake_data['weight']}\n"
        if symptom_intake_data.get("race"):
            symptom_intake_context += f"Race/Ethnicity: {symptom_intake_data['race']}\n"
        if symptom_intake_data.get("occupation"):
            symptom_intake_context += f"Occupation: {symptom_intake_data['occupation']}\n"
        if symptom_intake_data.get("symptoms"):
            symptom_intake_context += f"Initial Symptoms: {', '.join(symptom_intake_data['symptoms'])}\n"
        if symptom_intake_data.get("duration_months"):
            symptom_intake_context += f"Symptom Duration: {symptom_intake_data['duration_months']} months\n"
        if symptom_intake_data.get("environmental_factors"):
            symptom_intake_context += f"Environmental Factors: {', '.join(symptom_intake_data['environmental_factors'])}\n"
        if symptom_intake_data.get("life_stressors"):
            symptom_intake_context += f"Life Stressors: {symptom_intake_data['life_stressors']}\n"
        if symptom_intake_data.get("prior_diagnoses"):
            symptom_intake_context += f"Prior Diagnoses: {', '.join(symptom_intake_data['prior_diagnoses'])}\n"
        symptom_intake_context += "\n"

    if query_engine is None:
        try:
            from nlp_engines.vector_stores.postgresql_query_engine import PostgreSQLMedicalQueryEngine
            query_engine = PostgreSQLMedicalQueryEngine()
        except ImportError:
            from nlp_engines.vector_stores.query_engine import MedicalQueryEngine
            import os
            query_engine = MedicalQueryEngine("./vector_stores")

    query_text = journal_entry.notes if journal_entry.notes else ""
    for symptom in journal_entry.symptoms:
        query_text += f" {symptom.symptom}"

    all_results = await query_engine.query_all_collections(query_text) if hasattr(query_engine, 'query_all_collections') and asyncio.iscoroutinefunction(query_engine.query_all_collections) else query_engine.query_all_collections(query_text)

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

{symptom_intake_context}

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

You MUST categorize each sentence carefully and separately. Every sentence MUST be placed in a category.
- Symptoms are physical or mental health complaints (pain, fatigue, rashes, mood changes)
- Environmental factors are external elements like diet, food, allergens, weather, or exposures
- Life stressors are personal situations causing emotional stress (relationships, work, finances, pets)

DO NOT combine multiple sentences into a single category item. Each sentence should be analyzed individually.

Each sentence may contain multiple categories or none at all. Be thorough and precise in your categorization.

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
        print("\n=== JOURNAL ENTRY PROMPT ===")
        print(prompt)
        
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a medical AI assistant specializing in autoimmune diseases and the 2OPMD Diagnostic Terrain System."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        print("\n=== OPENAI RESPONSE ===")
        print(response.choices[0].message['content'])

        content = response.choices[0].message['content']

        print("\n=== RAW CONTENT FROM OPENAI ===")
        print(content)

        if content.startswith("```json") or content.startswith("```"):
            start_idx = content.find("\n") + 1
            end_idx = content.rfind("```")

            if end_idx > start_idx:
                content = content[start_idx:end_idx].strip()
            else:
                content = content[start_idx:].strip()
        
        try:
            analysis = json.loads(content)
            analysis["timestamp"] = datetime.now().isoformat()
            
            print("\n=== PARSED JSON ===")
            print(json.dumps(analysis, indent=2))
            
            if "symptoms" not in analysis:
                analysis["symptoms"] = []
            if "environmental_factors" not in analysis:
                analysis["environmental_factors"] = []
            if "life_stressors" not in analysis:
                analysis["life_stressors"] = []
            if "analysis" not in analysis:
                analysis["analysis"] = "No analysis provided."
                
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
        except json.JSONDecodeError as e:
            print(f"\n=== JSON PARSING ERROR ===")
            print(f"Error: {e}")
            print(f"Content: {content}")
            return {
                "analysis": "Unable to parse OpenAI response.",
                "symptoms": [],
                "environmental_factors": [],
                "life_stressors": [],
                "diagnoses": [],
                "timestamp": datetime.now().isoformat()
            }
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
