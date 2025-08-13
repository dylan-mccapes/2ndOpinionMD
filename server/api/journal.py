import openai
import os
from dotenv import load_dotenv
import json


openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")


@router.delete("/journal/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    entry_id: str,
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
        if "followUpQuestions" in analysis and analysis["followUpQuestions"]:
            entry_text += "Follow-up Questions:\n"
            for i, question in enumerate(analysis["followUpQuestions"], 1):
                entry_text += f"{i}. {question}\n"
        if "trackingSuggestions" in analysis and analysis["trackingSuggestions"]:
            entry_text += "Tracking Suggestions:\n"
            for i, suggestion in enumerate(analysis["trackingSuggestions"], 1):
                entry_text += f"{i}. {suggestion}\n"
    previous_entries_text = ""
    if previous_entries:
        previous_entries_text = "PREVIOUS JOURNAL ENTRIES:\n\n"
        for i, entry in enumerate(previous_entries, 1):
            entry_text = await format_journal_entry_for_prompt(entry)
            previous_entries_text += f"--- ENTRY {i} ---\n{entry_text}\n\n"

CURRENT JOURNAL ENTRY:
{current_entry_text}

                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
            if end_idx > start_idx:
                content = content[start_idx:end_idx].strip()
            else:
                content = content[start_idx:].strip()
        
    except Exception as e:
        print(f"Error generating journal analysis: {e}")
        return {
            "analysis": "Unable to generate analysis at this time.",
        }
