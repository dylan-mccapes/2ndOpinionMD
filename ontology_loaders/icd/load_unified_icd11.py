#!/usr/bin/env python3
"""
Unified ICD-11 Loader with Vector Embeddings
Loads ICD-11 data from TSV format into unified ontology.icd table
"""

import asyncio
import openai
import psycopg2
import csv
import sys
import os
from dotenv import load_dotenv
import numpy as np
from pathlib import Path

project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

openai.api_key = os.getenv("OPENAI_API_KEY")

async def get_embedding(text: str):
    """Generate mock embedding for testing (following existing pattern)"""
    return np.random.random(1536).tolist()

def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            dbname="knowledgegraph",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        sys.exit(1)

def parse_icd11_hierarchy(title, depth_in_kind):
    """Parse ICD-11 hierarchy from title and depth"""
    clean_title = title.strip().strip('"')
    
    dash_count = 0
    for char in title:
        if char == '-':
            dash_count += 1
        elif char == ' ':
            continue
        else:
            break
    
    clean_title = clean_title.lstrip('- ').strip('"')
    
    return clean_title, dash_count

def find_parent_from_code(code, existing_codes):
    """Find parent code based on ICD-11 code structure"""
    if not code or code == '_NOCODEASSIGNED':
        return None
    
    if '.' in code:
        parent_candidate = code.rsplit('.', 1)[0]
        if parent_candidate in existing_codes:
            return parent_candidate
    
    if len(code) > 2:
        for i in range(len(code) - 1, 1, -1):
            parent_candidate = code[:i]
            if parent_candidate in existing_codes:
                return parent_candidate
    
    return None

async def load_icd11_data(file_path):
    """Load ICD-11 data with embeddings"""
    print(f"Loading ICD-11 data from: {file_path}")
    
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    records = []
    existing_codes = set()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]
        
        reader = csv.DictReader(content.splitlines(), delimiter='\t')
        
        print(f"Processing ICD-11 TSV data...")
        
        for row_num, row in enumerate(reader, 1):
            foundation_uri = row.get('Foundation URI', '').strip()
            linearization_uri = row.get('Linearization (release) URI', '').strip()
            code = row.get('Code', '').strip()
            block_id = row.get('BlockId', '').strip()
            title = row.get('Title', '').strip()
            class_kind = row.get('ClassKind', '').strip()
            depth_in_kind = row.get('DepthInKind', '').strip()
            is_residual = row.get('IsResidual', '').strip().lower() == 'true'
            primary_location = row.get('PrimaryLocation', '').strip().lower() == 'true'
            chapter_no = row.get('ChapterNo', '').strip()
            
            if not foundation_uri and not code:
                continue
            
            if not code or code == '_NOCODEASSIGNED':
                if block_id:
                    code = block_id
                else:
                    code = f"ICD11_{row_num}"
            
            if code in existing_codes:
                code = f"{code}_{row_num}"
            
            clean_title, dash_count = parse_icd11_hierarchy(title, depth_in_kind)
            
            try:
                depth = int(depth_in_kind) if depth_in_kind.isdigit() else dash_count
            except:
                depth = dash_count
            
            parent_code = find_parent_from_code(code, existing_codes)
            
            search_content = f"ICD-11 {code}: {clean_title}"
            if class_kind:
                search_content += f" ({class_kind})"
            
            embedding = await get_embedding(search_content)
            
            full_path = [code]
            
            record = {
                'code': code,
                'title': clean_title,
                'definition': clean_title,  # ICD-11 doesn't have separate definition
                'system': 'ICD-11',
                'version': '2026',
                'parent_code': parent_code,
                'chapter': chapter_no if chapter_no else None,
                'section': None,
                'full_path': full_path,
                'depth': depth,
                'search_content': search_content,
                'foundation_uri': foundation_uri if foundation_uri else None,
                'linearization_uri': linearization_uri if linearization_uri else None,
                'class_kind': class_kind if class_kind else 'category',
                'is_residual': is_residual,
                'metadata': {
                    'source': 'icd11_tsv',
                    'block_id': block_id,
                    'primary_location': primary_location,
                    'dash_count': dash_count
                },
                'term_vector': embedding
            }
            
            if code not in existing_codes:
                records.append(record)
                existing_codes.add(code)
            else:
                print(f"Warning: Skipping duplicate code {code} at row {row_num}")
            
            if row_num % 1000 == 0:
                print(f"Processed {row_num} ICD-11 rows...")
    
    print(f"Parsed {len(records)} valid ICD-11 codes")
    
    code_to_record = {r['code']: r for r in records}
    
    for record in records:
        if not record['parent_code']:
            record['parent_code'] = find_parent_from_code(record['code'], existing_codes)
        
        path = []
        current = record
        visited = set()
        
        while current and current['code'] not in visited:
            visited.add(current['code'])
            path.insert(0, current['code'])
            if current['parent_code'] and current['parent_code'] in code_to_record:
                current = code_to_record[current['parent_code']]
            else:
                break
        
        record['full_path'] = path
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        print("Inserting ICD-11 data...")
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='icd' AND column_name='term_vector'")
        has_vector = cur.fetchone() is not None
        
        if has_vector:
            insert_query = """
                INSERT INTO ontology.icd
                (code, title, definition, system, version, parent_code, chapter, section, 
                 full_path, depth, search_content, foundation_uri, linearization_uri, 
                 class_kind, is_residual, metadata, term_vector)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        else:
            insert_query = """
                INSERT INTO ontology.icd
                (code, title, definition, system, version, parent_code, chapter, section, 
                 full_path, depth, search_content, foundation_uri, linearization_uri, 
                 class_kind, is_residual, metadata, term_vector_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        
        root_records = [r for r in records if r['parent_code'] is None]
        import json
        for record in root_records:
            if has_vector:
                cur.execute(insert_query, (
                    record['code'], record['title'], record['definition'], record['system'],
                    record['version'], record['parent_code'], record['chapter'], record['section'],
                    record['full_path'], record['depth'], record['search_content'],
                    record['foundation_uri'], record['linearization_uri'], record['class_kind'],
                    record['is_residual'], json.dumps(record['metadata']), record['term_vector']
                ))
            else:
                cur.execute(insert_query, (
                    record['code'], record['title'], record['definition'], record['system'],
                    record['version'], record['parent_code'], record['chapter'], record['section'],
                    record['full_path'], record['depth'], record['search_content'],
                    record['foundation_uri'], record['linearization_uri'], record['class_kind'],
                    record['is_residual'], json.dumps(record['metadata']), json.dumps(record['term_vector'])
                ))
        conn.commit()
        print(f"Inserted {len(root_records)} root ICD-11 records")
        
        remaining_records = [r for r in records if r['parent_code'] is not None]
        inserted_count = len(root_records)
        
        while remaining_records:
            batch_inserted = []
            
            for record in remaining_records[:]:
                parent_code = record['parent_code']
                
                cur.execute("SELECT 1 FROM ontology.icd WHERE code = %s", (parent_code,))
                if cur.fetchone():
                    try:
                        if has_vector:
                            cur.execute(insert_query, (
                                record['code'], record['title'], record['definition'], record['system'],
                                record['version'], record['parent_code'], record['chapter'], record['section'],
                                record['full_path'], record['depth'], record['search_content'],
                                record['foundation_uri'], record['linearization_uri'], record['class_kind'],
                                record['is_residual'], json.dumps(record['metadata']), record['term_vector']
                            ))
                        else:
                            cur.execute(insert_query, (
                                record['code'], record['title'], record['definition'], record['system'],
                                record['version'], record['parent_code'], record['chapter'], record['section'],
                                record['full_path'], record['depth'], record['search_content'],
                                record['foundation_uri'], record['linearization_uri'], record['class_kind'],
                                record['is_residual'], json.dumps(record['metadata']), json.dumps(record['term_vector'])
                            ))
                        batch_inserted.append(record)
                        remaining_records.remove(record)
                    except Exception as e:
                        print(f"Error inserting {record['code']}: {e}")
            
            if batch_inserted:
                conn.commit()
                inserted_count += len(batch_inserted)
                print(f"Inserted batch of {len(batch_inserted)} ICD-11 records (total: {inserted_count})")
            else:
                print(f"Warning: Could not insert {len(remaining_records)} records due to missing parents")
                break
        
        print(f"✅ Successfully loaded {inserted_count} ICD-11 codes")
        
    except Exception as e:
        print(f"Error during ICD-11 database operations: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "~/attachments/547b9ae0-85d3-437d-ad7b-55a2d4b93598/icd11-2026.txt"
    file_path = os.path.expanduser(file_path)
    asyncio.run(load_icd11_data(file_path))
