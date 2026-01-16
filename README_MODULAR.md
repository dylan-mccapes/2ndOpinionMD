# 2ndOpinionMD-MVP - Modular Architecture

## Overview
This repository has been restructured into a clean modular architecture for better maintainability, scalability, and development workflow.

## Directory Structure

```
/ontology_loaders/          # Medical ontology ETL systems
├── icd/                    # ICD-10-CM and ICD-11 loaders
│   ├── load_icd10cm.py     # Basic ICD-10-CM loader
│   ├── load_unified_icd10cm.py  # Advanced ICD-10-CM with embeddings
│   └── load_unified_icd11.py    # ICD-11 TSV loader with embeddings
├── legacy/                 # Deprecated loaders
│   └── load_icd10_data.py  # Legacy PostgreSQL loader
├── snomed/                 # Future SNOMED CT integration
├── hpo/                    # Future HPO integration
└── base_loader.py          # Common loader interface

/nlp_engines/               # NLP and vector search
├── embeddings/             # OpenAI embedding services
├── vector_stores/          # Database-specific implementations
│   ├── query_engine.py     # ChromaDB implementation
│   └── postgresql_query_engine.py  # pgvector implementation
├── query_engines/          # RAG and similarity search
└── unified_engine.py       # Database-agnostic interface

/api/                       # Unified FastAPI application
├── routes/                 # Endpoint definitions
├── middleware/             # Security, rate limiting
├── auth/                   # Authentication providers
└── main.py                 # Single configurable app

/database/                  # Schema and migration management
├── schemas/                # SQL schema definitions
│   ├── setup_knowledgegraph.sql  # Basic ontology schema
│   └── unified_icd_schema.sql     # Advanced unified schema
├── migrations/             # Database migration scripts
└── models/                 # ORM model definitions
    ├── postgresql/         # PostgreSQL models
    └── mongodb/            # MongoDB models

/shared/                    # Common utilities
├── config/                 # Configuration management
│   └── settings.py         # Unified settings
├── utils/                  # Shared utility functions
└── models/                 # Pydantic model definitions
```

## Migration Benefits

1. **Clear Separation of Concerns**: Each directory has single responsibility
2. **Scalable Architecture**: Easy to add new ontologies and platforms
3. **Reduced Duplication**: Shared utilities and interfaces
4. **Improved Testing**: Isolated components for unit testing
5. **Better Documentation**: Organized structure for API documentation
6. **Future-Proof**: Ready for SNOMED CT, HPO, and mobile development

## Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL with pgvector extension

### Installation
```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Running the Application
```bash
# Start the API server
cd server
python -m uvicorn api.app_postgres:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration

The application now uses unified configuration management through `shared/config/settings.py`. Key settings:

- `DATABASE_TYPE`: Choose between "postgresql", "mongodb", or "dual"
- `VECTOR_ENGINE`: Choose between "pgvector" or "chromadb"
- `OPENAI_API_KEY`: Required for embeddings and AI analysis

## Development Workflow

1. **Ontology Loaders**: Add new medical ontologies in `/ontology_loaders/`
2. **NLP Engines**: Extend vector search capabilities in `/nlp_engines/`
3. **API Endpoints**: Add new routes in `/server/api/`
4. **Database Changes**: Manage schemas in `/database/schemas/`

## Testing

```bash
# Run Python tests
pytest
```

## Deployment

The modular structure supports various deployment strategies:
- Containerized deployment with Docker
- Serverless deployment for API components

## Contributing

1. Follow the modular structure when adding new features
2. Use the base classes and interfaces provided
3. Update documentation when adding new components
4. Run tests before submitting changes

## Next Steps

1. Implement SNOMED CT loader in `/ontology_loaders/snomed/`
2. Add HPO integration in `/ontology_loaders/hpo/`
3. Enhance vector search capabilities in `/nlp_engines/`
4. Add comprehensive testing suite
