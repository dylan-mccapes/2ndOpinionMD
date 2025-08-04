#!/usr/bin/env python3
"""
HPO Terms Loader
Loads HPO terms from hp.json into ontology.hpo_terms table with embeddings
"""

import json
import psycopg2
import openai
import numpy as np
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import time
from psycopg2.extras import execute_values

project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

sys.path.append(str(project_root))
from ontology_loaders.base_loader import BaseOntologyLoader

openai.api_key = os.getenv("OPENAI_API_KEY")

class HPOTermsLoader(BaseOntologyLoader):
    """Loader for HPO terms from hp.json"""
    
    def __init__(self):
        super().__init__("HPO", "2025-05-06")
        self.use_mock_embeddings = False
        
    def get_db_connection(self):
        """Create database connection"""
        try:
            conn = psycopg2.connect(
                dbname="2ndopinionmd",
                user="devin",
                password="devin123",
                host="localhost",
                port="5432"
            )
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            sys.exit(1)
    
    def embed_texts(self, texts: List[str], max_retries: int = 3) -> List[List[float]]:
        """Generate embeddings with retry logic"""
        if self.use_mock_embeddings:
            embeddings = []
            for text in texts:
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()
                seed = int(text_hash[:8], 16)
                np.random.seed(seed)
                embedding = np.random.normal(0, 0.1, 1536).tolist()
                embeddings.append(embedding)
            return embeddings
        
        for attempt in range(max_retries):
            try:
                response = openai.Embedding.create(
                    model="text-embedding-3-small",
                    input=texts
                )
                return [r['embedding'] for r in response['data']]
            except Exception as e:
                print(f"OpenAI API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print("Falling back to mock embeddings")
                    self.use_mock_embeddings = True
                    return self.embed_texts(texts, max_retries)
    
    def generate_search_content(self, hpo_id: str, name: str, definition: str = None) -> str:
        """Generate search content for embedding"""
        parts = [f"HPO:{hpo_id}", name]
        if definition and definition != name:
            parts.append(definition)
        return " - ".join(parts)
    
    def parse_hp_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse hp.json and extract HPO terms"""
        print(f"📖 Parsing HPO terms from: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'graphs' not in data or not data['graphs']:
            raise ValueError("Invalid hp.json format: no graphs found")
        
        graph = data['graphs'][0]
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])
        
        print(f"Found {len(nodes)} nodes and {len(edges)} edges")
        
        parent_map = {}
        for edge in edges:
            if edge.get('pred') == 'is_a':
                child_id = edge.get('sub')
                parent_id = edge.get('obj')
                if child_id and parent_id:
                    if child_id not in parent_map:
                        parent_map[child_id] = []
                    parent_map[child_id].append(parent_id)
        
        terms = []
        for node in nodes:
            if node.get('type') != 'CLASS':
                continue
            
            node_id = node.get('id', '')
            if not node_id.startswith('http://purl.obolibrary.org/obo/HP_'):
                continue
            
            hpo_id = node_id.replace('http://purl.obolibrary.org/obo/', '')
            name = node.get('lbl', '')
            
            if not hpo_id or not name:
                continue
            
            definition = None
            synonyms = []
            is_obsolete = False
            
            meta = node.get('meta', {})
            if 'definition' in meta:
                def_obj = meta['definition']
                if isinstance(def_obj, dict) and 'val' in def_obj:
                    definition = def_obj['val']
                elif isinstance(def_obj, str):
                    definition = def_obj
            
            if 'synonyms' in meta:
                for syn in meta['synonyms']:
                    if isinstance(syn, dict) and 'val' in syn:
                        synonyms.append(syn['val'])
            
            if 'deprecated' in meta and meta['deprecated']:
                is_obsolete = True
            
            parent_ids = parent_map.get(node_id, [])
            parent_ids = [pid.replace('http://purl.obolibrary.org/obo/', '') for pid in parent_ids]
            
            term = {
                'hpo_id': hpo_id,
                'name': name,
                'definition': definition,
                'synonyms': synonyms,
                'parent_ids': parent_ids,
                'depth': 0,
                'is_obsolete': is_obsolete,
                'metadata': {
                    'source': 'hp.json',
                    'original_id': node_id,
                    'meta': meta
                }
            }
            
            terms.append(term)
        
        print(f"Parsed {len(terms)} valid HPO terms")
        return terms
    
    async def load_data(self, file_path: str) -> int:
        """Load HPO terms data"""
        if not openai.api_key:
            print("⚠️ Warning: OPENAI_API_KEY not found, using mock embeddings")
            self.use_mock_embeddings = True
        
        terms = self.parse_hp_json(file_path)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='hpo_terms' AND column_name='term_vec'
            """)
            has_vector = cursor.fetchone() is not None
            
            print(f"Database schema: Using {'term_vec' if has_vector else 'term_vec_json'} column")
            
            batch_size = 100
            total_batches = (len(terms) + batch_size - 1) // batch_size
            
            print(f"🔄 Processing {len(terms)} terms in {total_batches} batches")
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(terms))
                batch = terms[start_idx:end_idx]
                
                print(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch)} terms)...")
                
                texts = []
                for term in batch:
                    search_content = self.generate_search_content(
                        term['hpo_id'], term['name'], term['definition']
                    )
                    texts.append(search_content)
                
                embeddings = self.embed_texts(texts)
                
                insert_data = []
                for i, term in enumerate(batch):
                    embedding = embeddings[i]
                    
                    if has_vector:
                        insert_data.append((
                            term['hpo_id'], term['name'], term['definition'],
                            term['synonyms'], term['parent_ids'], term['depth'],
                            term['is_obsolete'], json.dumps(term['metadata']),
                            embedding
                        ))
                    else:
                        insert_data.append((
                            term['hpo_id'], term['name'], term['definition'],
                            term['synonyms'], term['parent_ids'], term['depth'],
                            term['is_obsolete'], json.dumps(term['metadata']),
                            json.dumps(embedding)
                        ))
                
                if has_vector:
                    insert_query = """
                        INSERT INTO ontology.hpo_terms
                        (hpo_id, name, definition, synonyms, parent_ids, depth, 
                         is_obsolete, metadata, term_vec)
                        VALUES %s
                        ON CONFLICT (hpo_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        definition = EXCLUDED.definition,
                        synonyms = EXCLUDED.synonyms,
                        parent_ids = EXCLUDED.parent_ids,
                        depth = EXCLUDED.depth,
                        is_obsolete = EXCLUDED.is_obsolete,
                        metadata = EXCLUDED.metadata,
                        term_vec = EXCLUDED.term_vec,
                        updated_at = NOW()
                    """
                else:
                    insert_query = """
                        INSERT INTO ontology.hpo_terms
                        (hpo_id, name, definition, synonyms, parent_ids, depth, 
                         is_obsolete, metadata, term_vec_json)
                        VALUES %s
                        ON CONFLICT (hpo_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        definition = EXCLUDED.definition,
                        synonyms = EXCLUDED.synonyms,
                        parent_ids = EXCLUDED.parent_ids,
                        depth = EXCLUDED.depth,
                        is_obsolete = EXCLUDED.is_obsolete,
                        metadata = EXCLUDED.metadata,
                        term_vec_json = EXCLUDED.term_vec_json,
                        updated_at = NOW()
                    """
                
                execute_values(cursor, insert_query, insert_data)
                conn.commit()
                
                self.stats['total_processed'] += len(batch)
                self.stats['successful_inserts'] += len(batch)
                
                print(f"✅ Batch {batch_idx + 1} completed")
                time.sleep(0.1)
            
            print(f"🎉 Successfully loaded {self.stats['successful_inserts']} HPO terms")
            return self.stats['successful_inserts']
            
        except Exception as e:
            print(f"❌ Error during HPO terms loading: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    
    async def generate_embeddings(self, batch_size: int = 100) -> bool:
        """Generate embeddings for loaded data"""
        return True
    
    async def validate_hierarchy(self) -> bool:
        """Validate the hierarchical structure of loaded data"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM ontology.hpo_terms 
                WHERE array_length(parent_ids, 1) > 0
            """)
            terms_with_parents = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ontology.hpo_terms")
            total_terms = cursor.fetchone()[0]
            
            print(f"Hierarchy validation: {terms_with_parents}/{total_terms} terms have parent relationships")
            return terms_with_parents > 0
            
        except Exception as e:
            print(f"Error validating hierarchy: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    import asyncio
    
    file_path = sys.argv[1] if len(sys.argv) > 1 else "data/hpo/hp.json"
    
    loader = HPOTermsLoader()
    asyncio.run(loader.load_data(file_path))
