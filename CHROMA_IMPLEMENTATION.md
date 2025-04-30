# Chroma Vector Database Implementation for 2ndOpinionMD

This document outlines the implementation of a Chroma vector database for the 2ndOpinionMD application. The implementation provides a FastAPI endpoint for generating medical diagnoses using retrieval-augmented generation (RAG) with support for complex medical data structures.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Setup Instructions](#setup-instructions)
- [Data Processing](#data-processing)
- [API Usage](#api-usage)
- [React Integration](#react-integration)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

## Features

- **Case-Insensitive Field Handling**: Automatically normalizes field names across camelCase, PascalCase, and snake_case
- **Intelligent Data Type Detection**: Automatically detects and processes different types of medical data
- **Multiple Collection Types**: Organizes data into appropriate collections without "profile" suffixes
- **Comprehensive Medical Data Support**: Handles case studies, diseases, conditions, autoimmune disorders, patients, and citations
- **Cost-Effective RAG**: Uses OpenAI's embedding model (text-embedding-3-small) and GPT-3.5-turbo for efficient retrieval-augmented generation

## Architecture

The implementation consists of the following components:

```
server/
├── api/
│   └── app.py                  # FastAPI server
├── examples/
│   ├── process_medical_data.py # Example for processing medical data
│   ├── query_medical_data.py   # Example for querying medical data
│   └── react_integration.js    # Example React integration
├── utils/
│   └── normalized_data_processor.py # Core module for data processing
├── vectordb/
│   ├── chroma_setup.py         # Script for setting up Chroma
│   └── query_engine.py         # Query engine for retrieving data
├── setup.sh                    # Setup script
└── requirements.txt            # Python dependencies
```

### Component Descriptions

- **app.py**: FastAPI server that exposes an API endpoint for generating medical diagnoses using RAG
- **normalized_data_processor.py**: Core module for handling case inconsistencies in JSON field names and creating appropriate collection names
- **chroma_setup.py**: Script for setting up Chroma collections for different types of medical data
- **query_engine.py**: Provides a comprehensive query engine for retrieving and processing medical data
- **process_medical_data.py**: Example script for processing medical data
- **query_medical_data.py**: Example script for querying medical data
- **react_integration.js**: Example React component for integrating with the API

## Setup Instructions

### 1. Install Dependencies

```bash
# Navigate to the server directory
cd server

# Run the setup script
chmod +x setup.sh
./setup.sh
```

This will:
- Create a Python virtual environment
- Install required dependencies
- Create a default .env file
- Create the Chroma database directory

### 2. Update the `.env` File

Edit the `.env` file in the server directory:

```
OPENAI_API_KEY=your-openai-api-key-here
CHROMA_PERSIST_DIR=./chroma_db
PORT=3001
HOST=0.0.0.0
```

### 3. Prepare Your Medical Data

Create a JSON file with your medical data. The system supports various data structures:

```json
{
  "case_studies": [
    {
      "case_id": "AIDx-0002",
      "primary_condition": "Rheumatoid Arthritis",
      "symptom_timeline": [
        "Intermittent aching pain and stiffness in small hand joints",
        "Persistent symmetric joint swelling and warmth in wrists and fingers"
      ],
      "misdiagnosed_as": ["Osteoarthritis", "Fibromyalgia"]
    }
  ],
  "DiseaseProfiles": [
    {
      "DiseaseName": "Myasthenia Gravis",
      "IcdCode": "G70.00",
      "CommonSymptoms": ["Muscle weakness", "Drooping eyelids"]
    }
  ],
  "diseaseProfiles": [
    {
      "diseaseName": "Lupus",
      "icdCode": "M32.9",
      "commonSymptoms": ["Butterfly-shaped rash", "Joint pain"]
    }
  ],
  "citations": [
    {
      "citation_id": "CIT000001",
      "citation_type": "Peer-Reviewed Article",
      "title": "Misdiagnosis Patterns in Autoimmune Disease",
      "authors_or_organization": "Smith, J.; Johnson, M.",
      "disease_relevance": ["Rheumatoid Arthritis", "Lupus"]
    }
  ]
}
```

Save this file as `medical_data.json` in your project directory.

### 4. Load Your Data into Chroma

```bash
# Activate the virtual environment
source venv/bin/activate

# Process your medical data
python vectordb/chroma_setup.py path/to/your/medical_data.json
```

### 5. Start the Server

```bash
# Activate the virtual environment
source venv/bin/activate

# Start the server
python api/app.py
```

The server will be available at http://localhost:3001.

## Data Processing

The system automatically processes different types of medical data:

### Supported Data Types

- **Case Studies**: Patient cases with symptom timelines and misdiagnosis patterns
- **Diseases**: Disease profiles with symptoms, lab markers, and diagnostic criteria
- **Conditions**: Medical conditions with zone scores and symbolic terrain tags
- **Autoimmune**: Autoimmune-specific information with immune risk levels
- **Patients**: Patient profiles with demographics and symptom data
- **Citations**: Medical research citations with relevance to specific diseases

### Case-Insensitive Field Handling

The system automatically normalizes field names across different case styles:

- **camelCase**: `diseaseName` → `disease_name`
- **PascalCase**: `DiseaseName` → `disease_name`
- **snake_case**: `disease_name` → `disease_name`

This ensures that your data is processed correctly regardless of the case style used.

### Collection Names

The system creates appropriate collection names without "profile" suffixes:

- `disease` (instead of `disease_profile`)
- `case`
- `condition`
- `autoimmune`
- `patient`
- `citation`

## API Usage

### Generate a Diagnosis

**Endpoint**: `POST /api/diagnose`

**Request**:

```json
{
  "symptoms": ["joint_pain", "fatigue", "fever"],
  "model": "gpt-3.5-turbo"
}
```

**cURL Example**:

```bash
curl -X POST http://localhost:3001/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"symptoms": ["joint_pain", "fatigue", "fever"], "model": "gpt-3.5-turbo"}'
```

**Response**:

```json
{
  "diagnoses": [
    {
      "name": "Rheumatoid Arthritis",
      "confidence": 85,
      "explanation": "Your symptoms of joint pain and fatigue are classic signs of rheumatoid arthritis...",
      "redFlags": ["Symmetric joint involvement", "Morning stiffness lasting >1 hour"],
      "labSuggestions": ["RF factor", "Anti-CCP antibodies", "CRP", "ESR"]
    }
  ]
}
```

### Health Check

**Endpoint**: `GET /api/health`

**cURL Example**:

```bash
curl http://localhost:3001/api/health
```

**Response**:

```json
{
  "status": "ok"
}
```

## React Integration

To integrate with your React frontend, update your `SymptomIntakeForm.js` component:

```javascript
// In your SymptomIntakeForm.js
const processForm = async (data) => {
  const formattedData = formatSymptomData(data);
  setJsonOutput(formattedData);
  
  try {
    const symptoms = data.symptoms.map(s => s.value);
    const response = await fetch('http://localhost:3001/api/diagnose', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ symptoms }),
    });
    
    const result = await response.json();
    onSubmit(result.diagnoses); // Pass the AI-generated diagnoses
  } catch (error) {
    console.error('Error fetching diagnosis:', error);
    // Fallback to your existing simulation
    onSubmit(data);
  }
};
```

See the `examples/react_integration.js` file for a complete React component example.

## Advanced Usage

### Processing Complex JSON Structures

```python
from utils.normalized_data_processor import process_medical_data_file

# Process a JSON file with mixed case styles
processed_data = process_medical_data_file("path/to/your/data.json")

# Print the processed data
for item in processed_data:
    print(f"Type: {item['type']}, ID: {item['id']}")
    print(item['text'])
    print("---")
```

### Custom Collection Creation

```python
import chromadb
from chromadb.utils import embedding_functions
from utils.normalized_data_processor import process_medical_data_file, create_chroma_collections

# Process your data
processed_data = process_medical_data_file("path/to/your/data.json")

# Set up OpenAI embeddings
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="your-openai-api-key",
    model_name="text-embedding-3-small"
)

# Initialize Chroma client
client = chromadb.PersistentClient(path="./chroma_db")

# Create collections
create_chroma_collections(processed_data, client, openai_ef)
```

### Direct Query Engine Usage

```python
from vectordb.query_engine import MedicalQueryEngine

# Initialize the query engine
engine = MedicalQueryEngine(persist_directory="./chroma_db")

# Query for symptoms
symptoms = ["joint_pain", "fatigue", "morning_stiffness"]
response = engine.generate_rag_response(symptoms, model="gpt-3.5-turbo")

# Print the response
print(response)
```

## Troubleshooting

### Common Issues

#### OpenAI API Key Not Found

If you see an error like `ValueError: OPENAI_API_KEY environment variable not set`, make sure you've updated the `.env` file with your OpenAI API key.

#### Chroma Database Not Found

If you see an error related to the Chroma database not being found, make sure you've run the `chroma_setup.py` script to create the database.

#### No Results from Queries

If your queries return no results, make sure you've loaded data into the Chroma database using the `chroma_setup.py` script.

### Getting Help

If you encounter any issues not covered here, please contact the development team at nate@2ndopinionmd.ai.
