# 2ndOpinionMD Vector Database Server

FastAPI server for 2ndOpinionMD.ai - AI-powered second opinions for autoimmune disease diagnosis with Chroma vector database integration.

## Features

- **Case-Insensitive Field Handling**: Automatically normalizes field names across camelCase, PascalCase, and snake_case
- **Intelligent Data Type Detection**: Automatically detects and processes different types of medical data
- **Multiple Collection Types**: Organizes data into appropriate collections without "profile" suffixes
- **Comprehensive Medical Data Support**: Handles case studies, diseases, conditions, autoimmune disorders, patients, and citations
- **Cost-Effective RAG**: Uses OpenAI's embedding model (text-embedding-3-small) and GPT-3.5-turbo for efficient retrieval-augmented generation

## Prerequisites

- Python 3.9+
- OpenAI API key

## Installation

1. Clone the repository
2. Run the setup script

```bash
cd server
chmod +x setup.sh
./setup.sh
```

3. Configure environment variables in `.env` file

```
OPENAI_API_KEY=your-openai-api-key-here
CHROMA_PERSIST_DIR=./chroma_db
PORT=3001
HOST=0.0.0.0
```

## Running the Server

### Development

```bash
source venv/bin/activate
python api/app.py
```

### Production

```bash
source venv/bin/activate
uvicorn api.app:app --host 0.0.0.0 --port 3001
```

## Chroma Vector Database Integration

This server uses Chroma for vector database storage. The following collections are defined:

- `disease`: Disease profiles with symptoms, lab markers, and diagnostic criteria
- `case`: Patient cases with symptom timelines and misdiagnosis patterns
- `condition`: Medical conditions with zone scores and symbolic terrain tags
- `autoimmune`: Autoimmune-specific information with immune risk levels
- `patient`: Patient profiles with demographics and symptom data
- `citation`: Medical research citations with relevance to specific diseases

## Medical Data Structure

The server uses a consolidated `medical_data.json` file with the following structure:

```json
{
  "caseStudies": [
    {
      "caseId": "AIDx-0002",
      "primaryCondition": "Rheumatoid Arthritis",
      "symptomTimeline": [
        "Intermittent aching pain and stiffness in small hand joints",
        "Persistent symmetric joint swelling and warmth in wrists and fingers"
      ],
      "misdiagnosedAs": ["Osteoarthritis", "Fibromyalgia"]
    }
  ],
  "autoimmuneTags": [
    {
      "tagName": "#AutoimmuneDx_MyastheniaGravis",
      "type": "confirmedAutoimmuneDx",
      "immuneRiskLevel": "High",
      "mechanism": "Autoimmune antibodies target acetylcholine receptors",
      "followOnConditions": "Thymoma, respiratory failure, other autoimmune conditions",
      "zoneImpact": "+1.0 / +0.5",
      "symbolicMeaning": "Recurring muscle fatigue and weakness symbolize struggles..."
    }
  ],
  "citations": [
    {
      "citationId": "CIT000001",
      "citationType": "Peer-Reviewed Article",
      "title": "Misdiagnosis Patterns in Autoimmune Disease",
      "authorsOrOrganization": "Smith, J.; Johnson, M.",
      "diseaseRelevance": ["Rheumatoid Arthritis", "Lupus"]
    }
  ]
}
```

## API Endpoints

### Diagnosis

- `POST /api/diagnose` - Submit symptom data for diagnosis
- `GET /api/health` - Health check endpoint

### Example Request

```json
{
  "symptoms": ["joint_pain", "fatigue", "fever"],
  "model": "gpt-3.5-turbo"
}
```

### Example Response

```json
{
  "diagnoses": [
    {
      "name": "Rheumatoid Arthritis",
      "confidence": 85,
      "explanation": "Your symptoms of joint pain and fatigue are classic signs...",
      "redFlags": ["Symmetric joint involvement", "Morning stiffness lasting >1 hour"],
      "labSuggestions": ["RF factor", "Anti-CCP antibodies", "CRP", "ESR"]
    }
  ]
}
```

## Data Processing

The system automatically processes different types of medical data and normalizes field names across different case styles:

- **camelCase**: `diseaseName` → `disease_name`
- **PascalCase**: `DiseaseName` → `disease_name`
- **snake_case**: `disease_name` → `disease_name`

## Loading Data

To load your medical data into Chroma:

```bash
source venv/bin/activate
python vectordb/chroma_setup.py server/data/medical_data.json
```

## For More Information

See the detailed `CHROMA_IMPLEMENTATION.md` file in the root directory for comprehensive documentation on the Chroma vector database implementation.

## License

ISC
