# RAG Data Retrieval Process in 2ndOpinionMD-MVP

This document explains how the Retrieval Augmented Generation (RAG) data is retrieved from the vector database in the 2ndOpinionMD-MVP codebase.

## Overview

The 2ndOpinionMD-MVP application uses a RAG approach to enhance journal analysis with relevant medical information. This process combines user-provided journal entries with medical knowledge retrieved from a vector database to generate more accurate and contextually relevant analyses.

## Data Retrieval Flow

1. **Frontend to Backend**: 
   - The frontend sends journal text to the backend through the `/api/journal/journal` endpoint via the `processJournalEntry` function in `src/utils/openaiService.js`
   - This function prepares the journal data and makes a POST request to the backend API

2. **Vector Database Query**:
   - In `server/api/journal.py`, the `generate_journal_analysis` function processes the journal entry
   - It creates a `MedicalQueryEngine` instance from `server/vectordb/query_engine.py`
   - The query engine connects to the Chroma vector database stored in the directory specified by the `CHROMA_PERSIST_DIR` environment variable
   - The journal text and symptoms are used to create a query string:
   ```python
   query_text = journal_entry.notes if journal_entry.notes else ""
   for symptom in journal_entry.symptoms:
       query_text += f" {symptom.symptom}"
   all_results = query_engine.query_all_collections(query_text)
   ```

3. **RAG Data Processing**:
   - The retrieved data is formatted into a context section called `rag_context`
   - This includes information from different collections in the vector database:
     - "disease" collection: Potential related conditions
     - "autoimmune" collection: Autoimmune information
     - "case" collection: Similar case studies

4. **OpenAI Integration**:
   - The RAG context is included in the prompt sent to OpenAI
   - OpenAI analyzes the journal entry with the context from the vector database
   - The response includes:
     - Analysis text
     - Extracted symptoms
     - Environmental factors
     - Life stressors
     - Diagnoses with confidence scores, STAX levels, and zones

5. **Response to Frontend**:
   - The structured JSON response is sent back to the frontend
   - The frontend displays this information in the `JournalAnalysisDisplay.js` component

## Key Files

- **Frontend**: 
  - `src/utils/openaiService.js`: Handles API calls to the backend
  - `src/components/journal/JournalAnalysisDisplay.js`: Displays the RAG data

- **Backend**:
  - `server/api/journal.py`: Contains the API endpoint and journal analysis logic
  - `server/vectordb/query_engine.py`: Interfaces with the Chroma vector database
  - `server/vectordb/chroma_setup.py`: Sets up the Chroma collections

## Data Structure

The RAG data returned from the backend has the following structure:

```json
{
  "analysis": "Text analysis of the journal entry",
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
    {
      "name": "Diagnosis name",
      "confidence": 85,
      "status": "confirmed/new/eliminated",
      "staxLevel": 1,
      "zone": 2,
      "tags": ["#SuspectedDx_DiagnosisName", "#EarlyZoneShift"]
    }
  ],
  "journalingRecommendation": {
    "promptType": "Clinical/Somatic/Symbolic/Remission",
    "suggestedPrompt": "What was lost when health left?"
  },
  "followUpQuestions": [
    "question 1",
    "question 2"
  ],
  "trackingSuggestions": [
    "suggestion 1",
    "suggestion 2"
  ],
  "patternObservations": "Any patterns observed across journal entries"
}
```

## Importance of RAG Data

The RAG data is crucial for providing context-aware analysis of journal entries, helping to identify potential diagnoses and health patterns based on the user's symptoms and journal content. By combining the user's input with relevant medical information from the vector database, the system can provide more accurate and personalized insights.
