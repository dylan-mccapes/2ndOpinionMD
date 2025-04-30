import json
import os
from typing import Dict, List, Any

def load_medical_data(file_path: str) -> Dict[str, Any]:
    """
    Load medical data from a JSON file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing the medical data
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading medical data: {e}")
        return {}

def process_diagnostic_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process diagnostic data from the medical data JSON
    
    Args:
        data: Dictionary containing the medical data
        
    Returns:
        List of processed diagnostic data entries
    """
    processed_data = []
    
    diagnostics = data.get('diagnostics', [])
    
    for diagnostic in diagnostics:
        text = f"Condition: {diagnostic.get('name', '')}\n"
        
        symptoms = diagnostic.get('symptoms', [])
        if symptoms:
            text += f"Symptoms: {', '.join(symptoms)}\n"
        
        red_flags = diagnostic.get('redFlags', [])
        if red_flags:
            text += f"Red Flags: {', '.join(red_flags)}\n"
        
        lab_suggestions = diagnostic.get('labSuggestions', [])
        if lab_suggestions:
            text += f"Lab Suggestions: {', '.join(lab_suggestions)}\n"
            
        confidence = diagnostic.get('confidence', 0)
        if confidence:
            text += f"Confidence: {confidence}\n"
        
        processed_data.append({
            'id': diagnostic.get('name', '').lower().replace(' ', '_'),
            'text': text,
            'metadata': diagnostic
        })
    
    return processed_data

def process_research_articles(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process research articles from the medical data JSON
    
    Args:
        data: Dictionary containing the medical data
        
    Returns:
        List of processed research article entries
    """
    processed_data = []
    
    articles = data.get('research', [])
    
    for article in articles:
        text = f"Title: {article.get('title', '')}\n"
        
        abstract = article.get('abstract', '')
        if abstract:
            text += f"Abstract: {abstract}\n"
        
        authors = article.get('authors', [])
        if authors:
            text += f"Authors: {', '.join(authors)}\n"
        
        keywords = article.get('keywords', [])
        if keywords:
            text += f"Keywords: {', '.join(keywords)}\n"
            
        journal = article.get('journal', '')
        year = article.get('year', '')
        if journal and year:
            text += f"Published in {journal}, {year}\n"
        
        processed_data.append({
            'id': f"article_{len(processed_data)}",
            'text': text,
            'metadata': article
        })
    
    return processed_data
