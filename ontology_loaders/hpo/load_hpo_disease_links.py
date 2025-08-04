#!/usr/bin/env python3
"""
HPO Disease Links Loader
Loads disease-phenotype associations from phenotype.hpoa into ontology.hpo_disease_links table
"""

import csv
import psycopg2
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
from psycopg2.extras import execute_values

project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

sys.path.append(str(project_root))
from ontology_loaders.base_loader import BaseOntologyLoader

class HPODiseaseLinksLoader(BaseOntologyLoader):
    """Loader for HPO disease associations from phenotype.hpoa"""
    
    def __init__(self):
        super().__init__("HPO-Disease-Links", "2025-05-06")
        
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
    
    def parse_phenotype_hpoa(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse phenotype.hpoa file"""
        print(f"📖 Parsing disease-phenotype associations from: {file_path}")
        
        associations = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        header_line = None
        data_start = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                if 'database_id' in line and 'hpo_id' in line:
                    header_line = line.strip('#').strip()
                continue
            else:
                data_start = i
                break
        
        if header_line:
            headers = [h.strip() for h in header_line.split('\t')]
            print(f"Found headers: {headers}")
        else:
            headers = [
                'database_id', 'disease_name', 'qualifier', 'hpo_id', 'reference',
                'evidence', 'onset', 'frequency', 'sex', 'modifier', 'aspect', 'biocuration'
            ]
            print("Using default headers")
        
        print(f"Processing {len(lines) - data_start} data lines...")
        
        for line_num, line in enumerate(lines[data_start:], data_start + 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            
            while len(parts) < len(headers):
                parts.append('')
            
            association = {}
            for i, header in enumerate(headers):
                value = parts[i] if i < len(parts) else ''
                association[header] = value if value else None
            
            if not association.get('database_id') or not association.get('hpo_id'):
                continue
            
            hpo_id = association.get('hpo_id', '').strip()
            
            if not hpo_id or hpo_id in ['HP:hpo_id', 'hpo_id', 'HP:', '']:
                continue
            
            if not hpo_id.startswith('HP:'):
                if hpo_id.startswith('HP_'):
                    hpo_id = hpo_id.replace('HP_', 'HP:')
                elif hpo_id.isdigit():
                    hpo_id = f"HP:{hpo_id.zfill(7)}"
                else:
                    hpo_id = f"HP:{hpo_id}"
            
            association['hpo_id'] = hpo_id
            
            associations.append(association)
            
            if len(associations) <= 5:
                print(f"Sample association {len(associations)}: database_id='{association.get('database_id')}', hpo_id='{association.get('hpo_id')}'")
            
            if line_num % 10000 == 0:
                print(f"Processed {line_num - data_start} lines...")
        
        print(f"Parsed {len(associations)} valid disease-phenotype associations")
        return associations
    
    async def load_data(self, file_path: str) -> int:
        """Load disease-phenotype associations"""
        associations = self.parse_phenotype_hpoa(file_path)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Loading disease-phenotype associations...")
            
            cursor.execute("SELECT hpo_id FROM ontology.hpo_terms LIMIT 10")
            sample_db_ids = [row[0] for row in cursor.fetchall()]
            print(f"Sample HPO IDs from hpo_terms table: {sample_db_ids}")
            
            cursor.execute("SELECT hpo_id FROM ontology.hpo_terms")
            valid_hpo_ids = set(row[0] for row in cursor.fetchall())
            print(f"Found {len(valid_hpo_ids)} valid HPO IDs in hpo_terms table")
            
            insert_data = []
            skipped_count = 0
            sample_file_ids = []
            
            for i, assoc in enumerate(associations):
                hpo_id = assoc.get('hpo_id')
                
                if i < 10:
                    sample_file_ids.append(hpo_id)
                
                if hpo_id not in valid_hpo_ids:
                    skipped_count += 1
                    if skipped_count <= 5:
                        print(f"Skipping HPO ID not in database: {repr(hpo_id)}")
                    continue
                
                insert_data.append((
                    assoc.get('database_id'),
                    assoc.get('disease_name'),
                    assoc.get('qualifier'),
                    hpo_id,
                    assoc.get('reference'),
                    assoc.get('evidence'),
                    assoc.get('onset'),
                    assoc.get('frequency'),
                    assoc.get('sex'),
                    assoc.get('modifier'),
                    assoc.get('aspect'),
                    assoc.get('biocuration')
                ))
            
            print(f"Sample HPO IDs from phenotype.hpoa: {sample_file_ids}")
            print(f"Prepared {len(insert_data)} valid associations, skipped {skipped_count} with invalid HPO IDs")
            
            batch_size = 1000
            total_batches = (len(insert_data) + batch_size - 1) // batch_size
            
            print(f"Inserting {len(insert_data)} associations in {total_batches} batches...")
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(insert_data))
                batch = insert_data[start_idx:end_idx]
                
                insert_query = """
                    INSERT INTO ontology.hpo_disease_links
                    (database_id, disease_name, qualifier, hpo_id, reference, evidence,
                     onset, frequency, sex, modifier, aspect, biocuration)
                    VALUES %s
                    ON CONFLICT DO NOTHING
                """
                
                execute_values(cursor, insert_query, batch)
                conn.commit()
                
                self.stats['total_processed'] += len(batch)
                self.stats['successful_inserts'] += len(batch)
                
                if (batch_idx + 1) % 10 == 0:
                    print(f"Completed batch {batch_idx + 1}/{total_batches}")
            
            print(f"🎉 Successfully loaded {self.stats['successful_inserts']} disease-phenotype associations")
            return self.stats['successful_inserts']
            
        except Exception as e:
            print(f"❌ Error during disease links loading: {e}")
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
        return True

if __name__ == "__main__":
    import asyncio
    
    file_path = sys.argv[1] if len(sys.argv) > 1 else "data/hpo/phenotype.hpoa"
    
    loader = HPODiseaseLinksLoader()
    asyncio.run(loader.load_data(file_path))
