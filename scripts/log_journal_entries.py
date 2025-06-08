#!/usr/bin/env python3
"""
Script to log journal entries for a user from the MongoDB database.
Usage: python scripts/log_journal_entries.py user@example.com
"""

import sys
import os
import asyncio
from datetime import datetime
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from models.mongodb.database import journal_entries_collection, users_collection

async def log_user_journal_entries(user_email):
    """Log all journal entries for a specific user"""
    try:
        user = await users_collection.find_one({"email": user_email})
        if not user:
            print(f"User with email '{user_email}' not found.")
            return
        
        user_id = user.get('id') or str(user.get('_id'))
        print(f"Found user: {user.get('full_name')} ({user_email})")
        print(f"User ID: {user_id}")
        print("-" * 50)
        
        entries = await journal_entries_collection.find(
            {"user_id": user_id}
        ).sort("date", -1).to_list(length=None)
        
        if not entries:
            print("No journal entries found for this user.")
            return
        
        print(f"Found {len(entries)} journal entries:")
        print("=" * 50)
        
        for i, entry in enumerate(entries, 1):
            entry_date = entry.get('date', 'Unknown date')
            if isinstance(entry_date, datetime):
                entry_date = entry_date.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"\n--- Entry {i} ---")
            print(f"Date: {entry_date}")
            print(f"Entry ID: {entry.get('id', entry.get('_id'))}")
            
            symptoms = entry.get('symptoms', [])
            print(f"Symptoms ({len(symptoms)} items):")
            for symptom in symptoms:
                if isinstance(symptom, dict):
                    symptom_text = symptom.get('symptom', 'Unknown symptom')
                    severity = symptom.get('severity', 'N/A')
                    print(f"  • {symptom_text} (Severity: {severity}/10)")
                else:
                    print(f"  • {symptom}")
            
            env_factors = entry.get('environmental_factors', [])
            if env_factors:
                print(f"Environmental Factors ({len(env_factors)} items):")
                for factor in env_factors:
                    if isinstance(factor, dict):
                        factor_type = factor.get('factor_type', 'Unknown')
                        description = factor.get('description', 'No description')
                        print(f"  • {factor_type}: {description}")
                    else:
                        print(f"  • {factor}")
            
            ai_analysis = entry.get('ai_analysis', {})
            if ai_analysis:
                print("AI Analysis:")
                
                ai_symptoms = ai_analysis.get('symptoms', [])
                if ai_symptoms:
                    print(f"  AI-extracted symptoms ({len(ai_symptoms)} items):")
                    for symptom in ai_symptoms:
                        print(f"    • {symptom}")
                
                life_stressors = ai_analysis.get('life_stressors', [])
                if life_stressors:
                    print(f"  Life stressors ({len(life_stressors)} items):")
                    for stressor in life_stressors:
                        print(f"    • {stressor}")
                
                analysis_text = ai_analysis.get('analysis', '')
                if analysis_text:
                    print(f"  Analysis: {analysis_text[:100]}...")
                
                diagnoses = ai_analysis.get('diagnoses', [])
                if diagnoses:
                    print(f"  Diagnoses ({len(diagnoses)} items):")
                    for diagnosis in diagnoses:
                        if isinstance(diagnosis, dict):
                            name = diagnosis.get('name', 'Unknown')
                            confidence = diagnosis.get('confidence', 'N/A')
                            status = diagnosis.get('status', 'unknown')
                            print(f"    • {name} - {confidence}% confidence ({status})")
                        else:
                            print(f"    • {diagnosis}")
            
            notes = entry.get('notes', '')
            if notes:
                print(f"Notes: {notes[:100]}...")
            
            print("-" * 30)
        
        print(f"\nTotal entries logged: {len(entries)}")
        
    except Exception as e:
        print(f"Error logging journal entries: {e}")
        import traceback
        traceback.print_exc()

async def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/log_journal_entries.py user@example.com")
        sys.exit(1)
    
    user_email = sys.argv[1]
    await log_user_journal_entries(user_email)

if __name__ == "__main__":
    asyncio.run(main())
