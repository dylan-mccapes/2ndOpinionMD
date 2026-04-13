"""Static coding response fixture matching CodingReview.tsx schema."""
from __future__ import annotations

CODING_RESPONSE = {
    "probable_dx": [
        {
            "code": "M32.9",
            "description": "Systemic lupus erythematosus, unspecified",
            "system": "ICD-10-CM",
            "confidence": 0.87,
        },
        {
            "code": "201436003",
            "description": "Systemic lupus erythematosus (disorder)",
            "system": "SNOMED CT",
            "confidence": 0.85,
        },
    ],
    "differential_dx": [
        {
            "code": "M06.9",
            "description": "Rheumatoid arthritis, unspecified",
            "system": "ICD-10-CM",
            "confidence": 0.62,
        },
        {
            "code": "M35.00",
            "description": "Sjögren syndrome, unspecified",
            "system": "ICD-10-CM",
            "confidence": 0.41,
        },
        {
            "code": "M35.9",
            "description": "Systemic involvement of connective tissue, unspecified",
            "system": "ICD-10-CM",
            "confidence": 0.34,
        },
    ],
    "labs": [
        {
            "code": "4548-4",
            "description": "Hemoglobin A1c/Hemoglobin.total in Blood",
            "system": "LOINC",
            "confidence": 0.91,
        },
        {
            "code": "1988-5",
            "description": "C reactive protein [Mass/volume] in Serum or Plasma",
            "system": "LOINC",
            "confidence": 0.88,
        },
        {
            "code": "4537-7",
            "description": "Erythrocyte sedimentation rate",
            "system": "LOINC",
            "confidence": 0.82,
        },
    ],
    "medications": [
        {
            "code": "5521",
            "description": "Hydroxychloroquine",
            "system": "RxNorm",
            "confidence": 0.79,
        },
        {
            "code": "41493",
            "description": "Methotrexate",
            "system": "RxNorm",
            "confidence": 0.55,
        },
    ],
    "procedures": [
        {
            "code": "J3490",
            "description": "Unclassified biologics",
            "system": "HCPCS",
            "confidence": 0.38,
        },
    ],
}
