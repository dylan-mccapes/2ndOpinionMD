"""
Normalized data processor for 2ndOpinionMD-MVP
Handles case inconsistencies in JSON field names and creates appropriate collection names
"""

import json
import os
from typing import Dict, List, Any, Optional
import uuid
import re

def normalize_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize dictionary keys to lowercase with underscores
    
    Args:
        data: Dictionary with potentially inconsistent key casing
        
    Returns:
        Dictionary with normalized keys
    """
    if not isinstance(data, dict):
        return data
    
    normalized = {}
    for key, value in data.items():
        normalized_key = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
        
        if isinstance(value, list):
            normalized_value = [
                normalize_keys(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, dict):
            normalized_value = normalize_keys(value)
        else:
            normalized_value = value
            
        normalized[normalized_key] = normalized_value
    
    return normalized

def load_medical_data(file_path: str) -> Dict[str, Any]:
    """
    Load medical data from a JSON file and normalize keys
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing the normalized medical data
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        normalized_data = normalize_keys(data)
        return normalized_data
    except Exception as e:
        print(f"Error loading medical data: {e}")
        return {}

def process_case_study(case_study: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a case study JSON object
    
    Args:
        case_study: Dictionary containing case study data
        
    Returns:
        Processed case study data ready for vectorization
    """
    case_id = case_study.get('case_id', f"case_{uuid.uuid4().hex[:8]}")
    
    text = f"Case Study: {case_id}\n"
    
    if 'primary_condition' in case_study:
        text += f"Primary Condition: {case_study['primary_condition']}\n"
    
    if 'diagnostic_zone' in case_study:
        text += f"Diagnostic Zone: {case_study['diagnostic_zone']}\n"
    
    if 'stax_score' in case_study:
        text += f"STAX Score: {case_study['stax_score']}\n"
    
    if 'flare_type' in case_study:
        text += f"Flare Type: {case_study['flare_type']}\n"
    
    if 'symptom_timeline' in case_study and isinstance(case_study['symptom_timeline'], list):
        text += "Symptom Timeline:\n"
        for symptom in case_study['symptom_timeline']:
            text += f"- {symptom}\n"
    
    if 'misdiagnosed_as' in case_study and isinstance(case_study['misdiagnosed_as'], list):
        text += "Misdiagnosed As:\n"
        for misdiagnosis in case_study['misdiagnosed_as']:
            text += f"- {misdiagnosis}\n"
    
    if 'eventual_diagnosis_time' in case_study:
        text += f"Eventual Diagnosis Time: {case_study['eventual_diagnosis_time']} years\n"
    
    if 'ethos_terrain_tags' in case_study and isinstance(case_study['ethos_terrain_tags'], list):
        text += "Ethos Terrain Tags:\n"
        for tag in case_study['ethos_terrain_tags']:
            text += f"- {tag}\n"
    
    if 'suppressors' in case_study and isinstance(case_study['suppressors'], list):
        text += "Suppressors:\n"
        for suppressor in case_study['suppressors']:
            text += f"- {suppressor}\n"
    
    if 'annotated_case_summary' in case_study:
        text += f"Case Summary: {case_study['annotated_case_summary']}\n"
    
    if 'citations' in case_study and isinstance(case_study['citations'], list):
        text += "Citations:\n"
        for citation in case_study['citations']:
            text += f"- {citation}\n"
    
    return {
        'id': case_id,
        'text': text,
        'metadata': case_study,
        'type': 'case'
    }

def process_disease(disease: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a disease JSON object
    
    Args:
        disease: Dictionary containing disease data
        
    Returns:
        Processed disease data ready for vectorization
    """
    disease_name = disease.get('disease_name', disease.get('diseasename', ''))
    if not disease_name:
        disease_name = disease.get('name', '')
    
    disease_id = f"disease_{disease_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}"
    
    text = f"Disease: {disease_name}\n"
    
    icd_code = disease.get('icd_code', disease.get('icd10', ''))
    if icd_code:
        text += f"ICD Code: {icd_code}\n"
    
    symptoms = disease.get('common_symptoms', disease.get('symptoms', []))
    if symptoms and isinstance(symptoms, list):
        text += "Symptoms:\n"
        for symptom in symptoms:
            text += f"- {symptom}\n"
    
    adjacency_markers = disease.get('adjacency_markers', [])
    if adjacency_markers and isinstance(adjacency_markers, list):
        text += "Adjacency Markers:\n"
        for marker in adjacency_markers:
            text += f"- {marker}\n"
    
    autoimmune_indicators = disease.get('autoimmune_adjacent_indicators', [])
    if autoimmune_indicators and isinstance(autoimmune_indicators, list):
        text += "Autoimmune Adjacent Indicators:\n"
        for indicator in autoimmune_indicators:
            text += f"- {indicator}\n"
    
    threshold_indicators = disease.get('threshold_drift_indicators', [])
    if threshold_indicators and isinstance(threshold_indicators, list):
        text += "Threshold Drift Indicators:\n"
        for indicator in threshold_indicators:
            text += f"- {indicator}\n"
    
    symptom_drift = disease.get('parallel_symptom_drift_examples', [])
    if symptom_drift and isinstance(symptom_drift, list):
        text += "Parallel Symptom Drift Examples:\n"
        for example in symptom_drift:
            text += f"- {example}\n"
    
    diagnostic_constellation = disease.get('diagnostic_constellation', [])
    if diagnostic_constellation and isinstance(diagnostic_constellation, list):
        text += "Diagnostic Constellation:\n"
        for diagnostic in diagnostic_constellation:
            text += f"- {diagnostic}\n"
    
    misdiagnoses = disease.get('common_misdiagnoses', [])
    if misdiagnoses and isinstance(misdiagnoses, list):
        text += "Common Misdiagnoses:\n"
        for misdiagnosis in misdiagnoses:
            text += f"- {misdiagnosis}\n"
    
    lab_markers = disease.get('key_lab_markers', disease.get('lab_markers', []))
    if lab_markers and isinstance(lab_markers, list):
        text += "Lab Markers:\n"
        for marker in lab_markers:
            text += f"- {marker}\n"
    
    demographics = disease.get('demographics', {})
    if demographics and isinstance(demographics, dict):
        text += "Demographics:\n"
        for key, value in demographics.items():
            text += f"- {key}: {value}\n"
    
    prognosis = disease.get('prognosis', '')
    if prognosis:
        text += f"Prognosis: {prognosis}\n"
    
    symptom_profile = disease.get('symptom_profile', {})
    if symptom_profile and isinstance(symptom_profile, dict):
        text += "Symptom Profile:\n"
        for key, value in symptom_profile.items():
            text += f"- {key}: {value}\n"
    
    prevalence = disease.get('prevalence', '')
    if prevalence:
        text += f"Prevalence: {prevalence}\n"
    
    gender_dist = disease.get('gender_distribution', '')
    if gender_dist:
        text += f"Gender Distribution: {gender_dist}\n"
    
    ethnic_dist = disease.get('ethnic_distribution', '')
    if ethnic_dist:
        text += f"Ethnic Distribution: {ethnic_dist}\n"
    
    ethos = disease.get('ethos_of_health', {})
    if ethos and isinstance(ethos, dict):
        text += "Ethos of Health:\n"
        for key, value in ethos.items():
            if isinstance(value, list):
                text += f"- {key}:\n"
                for item in value:
                    text += f"  - {item}\n"
            else:
                text += f"- {key}: {value}\n"
    
    return {
        'id': disease_id,
        'text': text,
        'metadata': disease,
        'type': 'disease'
    }

def process_condition(condition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a condition JSON object
    
    Args:
        condition: Dictionary containing condition data
        
    Returns:
        Processed condition data ready for vectorization
    """
    condition_name = condition.get('condition', '')
    condition_id = f"condition_{condition_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}"
    
    text = f"Condition: {condition_name}\n"
    
    if 'zone_score' in condition:
        text += f"Zone Score: {condition['zone_score']}\n"
    
    if 'stax_score' in condition:
        text += f"STAX Score: {condition['stax_score']}\n"
    
    if 'symbolic_terrain_tags' in condition and isinstance(condition['symbolic_terrain_tags'], list):
        text += "Symbolic Terrain Tags:\n"
        for tag in condition['symbolic_terrain_tags']:
            text += f"- {tag}\n"
    
    if 'flare_type' in condition:
        text += f"Flare Type: {condition['flare_type']}\n"
    
    if 'suppression_logic_flags' in condition and isinstance(condition['suppression_logic_flags'], list):
        text += "Suppression Logic Flags:\n"
        for flag in condition['suppression_logic_flags']:
            text += f"- {flag}\n"
    
    if 'case_narrative' in condition:
        text += f"Case Narrative: {condition['case_narrative']}\n"
    
    if 'misdiagnosis_history' in condition:
        text += f"Misdiagnosis History: {condition['misdiagnosis_history']}\n"
    
    if 'symptom_timeline' in condition and isinstance(condition['symptom_timeline'], list):
        text += "Symptom Timeline:\n"
        for event in condition['symptom_timeline']:
            if isinstance(event, dict) and 'month' in event and 'event' in event:
                text += f"- Month {event['month']}: {event['event']}\n"
            else:
                text += f"- {event}\n"
    
    return {
        'id': condition_id,
        'text': text,
        'metadata': condition,
        'type': 'condition'
    }

def process_autoimmune(autoimmune: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an autoimmune JSON object
    
    Args:
        autoimmune: Dictionary containing autoimmune data
        
    Returns:
        Processed autoimmune data ready for vectorization
    """
    tag_name = autoimmune.get('tag_name', '')
    profile_id = f"autoimmune_{tag_name.lower().replace('#', '').replace('_', '').replace(' ', '_')}"
    
    text = f"Autoimmune: {tag_name}\n"
    
    if 'type' in autoimmune:
        text += f"Type: {autoimmune['type']}\n"
    
    if 'immune_risk_level' in autoimmune:
        text += f"Immune Risk Level: {autoimmune['immune_risk_level']}\n"
    
    if 'mechanism' in autoimmune:
        text += f"Mechanism: {autoimmune['mechanism']}\n"
    
    if 'follow_on_conditions' in autoimmune and isinstance(autoimmune['follow_on_conditions'], list):
        text += "Follow-on Conditions:\n"
        for condition in autoimmune['follow_on_conditions']:
            text += f"- {condition}\n"
    
    if 'zone_impact' in autoimmune:
        text += f"Zone Impact: {autoimmune['zone_impact']}\n"
    
    if 'symbolic_meaning' in autoimmune:
        text += f"Symbolic Meaning: {autoimmune['symbolic_meaning']}\n"
    
    return {
        'id': profile_id,
        'text': text,
        'metadata': autoimmune,
        'type': 'autoimmune'
    }

def process_patient(patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a patient JSON object
    
    Args:
        patient: Dictionary containing patient data
        
    Returns:
        Processed patient data ready for vectorization
    """
    profile_id = f"patient_{uuid.uuid4().hex[:8]}"
    
    text = "Patient:\n"
    
    if 'demographics' in patient and isinstance(patient['demographics'], dict):
        text += "Demographics:\n"
        for key, value in patient['demographics'].items():
            text += f"- {key}: {value}\n"
    
    if 'symptoms' in patient and isinstance(patient['symptoms'], list):
        text += "Symptoms:\n"
        for symptom in patient['symptoms']:
            text += f"- {symptom}\n"
    
    if 'diagnoses' in patient and isinstance(patient['diagnoses'], dict):
        if 'confirmed' in patient['diagnoses'] and isinstance(patient['diagnoses']['confirmed'], list):
            text += "Confirmed Diagnoses:\n"
            for diagnosis in patient['diagnoses']['confirmed']:
                text += f"- {diagnosis}\n"
        
        if 'suspected' in patient['diagnoses'] and isinstance(patient['diagnoses']['suspected'], list):
            text += "Suspected Diagnoses:\n"
            for diagnosis in patient['diagnoses']['suspected']:
                text += f"- {diagnosis}\n"
    
    if 'tags' in patient and isinstance(patient['tags'], dict):
        if 'core' in patient['tags'] and isinstance(patient['tags']['core'], list):
            text += "Core Tags:\n"
            for tag in patient['tags']['core']:
                text += f"- {tag}\n"
        
        if 'symbolic' in patient['tags'] and isinstance(patient['tags']['symbolic'], list):
            text += "Symbolic Tags:\n"
            for tag in patient['tags']['symbolic']:
                text += f"- {tag}\n"
        
        if 'stax_level' in patient['tags']:
            text += f"STAX Level: {patient['tags']['stax_level']}\n"
        
        if 'zone' in patient['tags']:
            text += f"Zone: {patient['tags']['zone']}\n"
        
        if 'symbolic_narrative' in patient['tags']:
            text += f"Symbolic Narrative: {patient['tags']['symbolic_narrative']}\n"
    
    return {
        'id': profile_id,
        'text': text,
        'metadata': patient,
        'type': 'patient'
    }

def process_citation(citation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a citation JSON object
    
    Args:
        citation: Dictionary containing citation data
        
    Returns:
        Processed citation data ready for vectorization
    """
    citation_id = citation.get('citation_id', f"citation_{uuid.uuid4().hex[:8]}")
    
    text = f"Citation: {citation_id}\n"
    
    if 'citation_type' in citation:
        text += f"Type: {citation['citation_type']}\n"
    
    if 'title' in citation:
        text += f"Title: {citation['title']}\n"
    
    if 'authors_or_organization' in citation:
        text += f"Authors/Organization: {citation['authors_or_organization']}\n"
    
    if 'publication_year' in citation:
        text += f"Year: {citation['publication_year']}\n"
    
    if 'journal_or_source_name' in citation:
        text += f"Journal/Source: {citation['journal_or_source_name']}\n"
    
    if 'volume_and_issue' in citation:
        text += f"Volume/Issue: {citation['volume_and_issue']}\n"
    
    if 'doi_or_url' in citation:
        text += f"DOI/URL: {citation['doi_or_url']}\n"
    
    if 'disease_relevance' in citation and isinstance(citation['disease_relevance'], list):
        text += "Disease Relevance:\n"
        for disease in citation['disease_relevance']:
            text += f"- {disease}\n"
    
    if 'key_findings' in citation and isinstance(citation['key_findings'], list):
        text += "Key Findings:\n"
        for finding in citation['key_findings']:
            text += f"- {finding}\n"
    
    if 'reasoning_tags' in citation and isinstance(citation['reasoning_tags'], list):
        text += "Reasoning Tags:\n"
        for tag in citation['reasoning_tags']:
            text += f"- {tag}\n"
    
    if 'reasoning_usage' in citation:
        text += f"Reasoning Usage: {citation['reasoning_usage']}\n"
    
    return {
        'id': citation_id,
        'text': text,
        'metadata': citation,
        'type': 'citation'
    }

def detect_data_type(data: Dict[str, Any]) -> str:
    """
    Detect the type of data based on its structure
    
    Args:
        data: Dictionary containing data
        
    Returns:
        String indicating the data type
    """
    if 'case_id' in data or 'primary_condition' in data:
        return 'case'
    
    if 'disease_name' in data or 'diseasename' in data or ('name' in data and 'symptom_profile' in data):
        return 'disease'
    
    if 'condition' in data or 'zone_score' in data:
        return 'condition'
    
    if 'tag_name' in data and 'immune_risk_level' in data:
        return 'autoimmune'
    
    if 'demographics' in data and 'symptoms' in data:
        return 'patient'
    
    if 'citation_id' in data or 'citation_type' in data:
        return 'citation'
    
    return 'unknown'

def process_medical_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a medical data object based on its detected type
    
    Args:
        data: Dictionary containing medical data
        
    Returns:
        Processed data ready for vectorization
    """
    normalized_data = normalize_keys(data)
    
    data_type = detect_data_type(normalized_data)
    
    if data_type == 'case':
        return process_case_study(normalized_data)
    elif data_type == 'disease':
        return process_disease(normalized_data)
    elif data_type == 'condition':
        return process_condition(normalized_data)
    elif data_type == 'autoimmune':
        return process_autoimmune(normalized_data)
    elif data_type == 'patient':
        return process_patient(normalized_data)
    elif data_type == 'citation':
        return process_citation(normalized_data)
    else:
        return {
            'id': f"unknown_{uuid.uuid4().hex[:8]}",
            'text': str(normalized_data),
            'metadata': normalized_data,
            'type': 'unknown'
        }

def process_medical_data_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Process a medical data file containing various JSON objects
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of processed data entries ready for vectorization
    """
    data = load_medical_data(file_path)
    processed_data = []
    
    if isinstance(data, list):
        for item in data:
            processed_data.append(process_medical_data(item))
        return processed_data
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                for item in value:
                    processed_data.append(process_medical_data(item))
        
        if not processed_data:
            processed_data.append(process_medical_data(data))
    
    return processed_data

def create_chroma_collections(processed_data: List[Dict[str, Any]], client, embedding_function):
    """
    Create Chroma collections from processed data
    
    Args:
        processed_data: List of processed data entries
        client: Chroma client
        embedding_function: Function to generate embeddings
    """
    data_by_type = {}
    for item in processed_data:
        item_type = item.get('type', 'unknown')
        if item_type not in data_by_type:
            data_by_type[item_type] = []
        data_by_type[item_type].append(item)
    
    for data_type, items in data_by_type.items():
        collection_name = f"{data_type}"
        
        try:
            collection = client.get_collection(name=collection_name, embedding_function=embedding_function)
            print(f"Collection {collection_name} already exists")
        except:
            collection = client.create_collection(name=collection_name, embedding_function=embedding_function)
            print(f"Created collection {collection_name}")
        
        ids = [item['id'] for item in items]
        documents = [item['text'] for item in items]
        metadatas = [item['metadata'] for item in items]
        
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"Added {len(items)} items to collection {collection_name}")

if __name__ == "__main__":
    import argparse
    import chromadb
    from chromadb.utils import embedding_functions
    from dotenv import load_dotenv
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(project_root, '.env')
    load_dotenv(env_path)
    
    parser = argparse.ArgumentParser(description="Process medical data and add to Chroma")
    parser.add_argument("file_path", help="Path to the medical data JSON file")
    parser.add_argument("--persist-dir", default="./chroma_db", help="Directory to persist the Chroma DB")
    
    args = parser.parse_args()
    
    processed_data = process_medical_data_file(args.file_path)
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name="text-embedding-3-small"
    )
    
    client = chromadb.PersistentClient(path=args.persist_dir)
    
    create_chroma_collections(processed_data, client, openai_ef)
    
    print(f"Successfully processed {len(processed_data)} items and added to Chroma")
