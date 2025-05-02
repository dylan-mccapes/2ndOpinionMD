# 2ndOpinionMD-MVP Troubleshooting Guide

This guide addresses common issues encountered when setting up and running the 2ndOpinionMD-MVP project.

## Configuration Files

### Root .env File

The main `.env` file is located in the root directory of the project. This file contains configuration for the frontend React application:

```
# === API KEYS ===
OPENAI_API_KEY=your-openai-api-key-here
BASTION_API_KEY=your-bastion-api-key-here

# === MODEL ROUTING CONFIG ===
DEFAULT_AI_MODEL=gpt-4-turbo
HIPAA_AI_MODEL=bastion
USE_HIPAA_MODE=true

# === APP CONFIGURATION ===
PORT=3000
DOMAIN_URL=http://localhost:3000

# === EMAIL SETTINGS ===
REPORT_EMAIL_FROM=nate@2ndopinionmd.ai
ENABLE_DARK_MODE=true
```

To modify the OpenAI model used by the frontend, change the `DEFAULT_AI_MODEL` value.

### Server .env File

The server `.env` file is created by the `setup.sh` script in the server directory. This file contains configuration for the backend FastAPI server:

```
OPENAI_API_KEY=your-openai-api-key-here
CHROMA_PERSIST_DIR=./chroma_db
PORT=3001
HOST=0.0.0.0
```

## Common Issues and Solutions

### 1. OpenAI Client Compatibility Error

**Error:**
```
TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
```

**Solution:**
This is a version compatibility issue between ChromaDB and the OpenAI Python client. Install an older version of the OpenAI package:

```zsh
pip uninstall openai -y
pip install openai==0.28.1
```

### 2. ChromaDB Metadata Format Error with Lists

**Error:**
```
ValueError: Expected metadata value to be a str, int, float or bool, got [...] which is a <class 'list'>
```

**Solution:**
ChromaDB expects metadata values to be simple types (string, int, float, bool) but the medical data contains lists in the metadata. You need to modify the metadata before adding it to ChromaDB.

1. Add the `sanitize_metadata_for_chroma` function from `fix_chroma_metadata.py` to your project.
2. Modify the `add_data_to_collections` function in `server/vectordb/chroma_setup.py`:

```python
def add_data_to_collections(collections, processed_data):
    # ... existing code ...
    
    # Add data to collections
    for data_type, items in data_by_type.items():
        if data_type in collections:
            collections[data_type].add(
                ids=[item["id"] for item in items],
                documents=[item["text"] for item in items],
                metadatas=[sanitize_metadata_for_chroma(item["metadata"]) for item in items]
            )
            print(f"Added {len(items)} {data_type} entries to ChromaDB")
```

3. Or modify the `create_chroma_collections` function in `server/utils/normalized_data_processor.py`:

```python
def create_chroma_collections(processed_data, client, embedding_function):
    # ... existing code ...
    
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=[sanitize_metadata_for_chroma(metadata) for metadata in metadatas]
    )
```

### 3. Python Version Compatibility

If you're using Python 3.13, you may encounter PyO3 compatibility issues. Use Python 3.10 or 3.12 instead, or set the environment variable:

```zsh
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
```

## Running the Server

After fixing these issues, you can run the server with:

```zsh
cd server
source venv/bin/activate
python api/app.py
```

The server will be available at http://localhost:3001.
