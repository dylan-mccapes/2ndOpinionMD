#!/usr/bin/env python3
"""
ICD-10-CM Data Loader for 2ndOpinionMD Knowledge Graph

This script parses the official ICD-10-CM hierarchy file and loads it into
the ontology.icd table in PostgreSQL with proper parent-child relationships
and full path breadcrumbs.
"""

import psycopg2
from pathlib import Path
from collections import deque
import sys
import os

def get_db_connection():
    """Create database connection with error handling"""
    import getpass
    
    connection_configs = [
        {
            "dbname": "knowledgegraph",
            "user": getpass.getuser(),
            "host": "localhost",
            "port": "5432"
        },
        {
            "dbname": "knowledgegraph",
            "user": "postgres",
            "password": "postgres",
            "host": "localhost",
            "port": "5432"
        },
        {
            "dbname": "knowledgegraph",
            "user": "postgres",
            "host": "localhost",
            "port": "5432"
        }
    ]
    
    for config in connection_configs:
        try:
            conn = psycopg2.connect(**config)
            print(f"Connected to database as user: {config['user']}")
            return conn
        except psycopg2.Error as e:
            continue
    
    print("Error: Could not connect to database with any configuration")
    print("Please ensure PostgreSQL is running and the knowledgegraph database exists")
    sys.exit(1)

def parse_icd_line(line):
    """Parse a single line from the ICD-10-CM file"""
    if len(line) < 59:
        return None
    
    order = line[0:5].strip()
    code = line[6:14].strip()
    flag = line[15:17].strip()
    short_desc = line[18:58].strip()
    long_desc = line[59:].strip()
    
    return {
        'order': order,
        'code': code,
        'flag': flag,
        'short_desc': short_desc,
        'long_desc': long_desc
    }

def get_hierarchy_level(code):
    """Determine hierarchy level based on code structure"""
    if not code:
        return 0
    
    clean_code = code.replace(".", "")
    
    if len(clean_code) <= 3:
        return 0  # Category level
    elif len(clean_code) == 4:
        return 1  # First subcategory
    elif len(clean_code) == 5:
        return 2  # Second subcategory
    else:
        return 3  # Further subcategories

def find_parent_code(code, stack):
    """Find the appropriate parent code based on hierarchy"""
    if not code or not stack:
        return None
    
    current_level = get_hierarchy_level(code)
    
    for parent_code, parent_level in reversed(stack):
        if parent_level < current_level:
            return parent_code
    
    return None

def load_icd10cm_data(file_path):
    """Main function to load ICD-10-CM data"""
    print(f"Loading ICD-10-CM data from: {file_path}")
    
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    print(f"Processing {len(lines)} lines...")
    
    records = []
    stack = deque()  # Stack to track hierarchy: [(code, level), ...]
    
    for line_num, line in enumerate(lines, 1):
        parsed = parse_icd_line(line.strip())
        
        if not parsed or not parsed['code']:
            continue
        
        code = parsed['code']
        level = get_hierarchy_level(code)
        
        while stack and stack[-1][1] >= level:
            stack.pop()
        
        parent_code = find_parent_code(code, stack)
        
        path_codes = [item[0] for item in stack] + [code]
        full_path = " > ".join(path_codes)
        
        record = (
            code,                    # code
            parsed['short_desc'],    # title
            parsed['long_desc'],     # definition
            'ICD-10-CM',            # version
            parent_code,            # parent_code
            None,                   # chapter (to be filled later if needed)
            None,                   # section (to be filled later if needed)
            full_path               # full_path
        )
        
        records.append(record)
        stack.append((code, level))
        
        if line_num % 1000 == 0:
            print(f"Processed {line_num} lines...")
    
    print(f"Parsed {len(records)} valid ICD-10-CM codes")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        print("Clearing existing ICD data...")
        cur.execute("TRUNCATE TABLE ontology.icd CASCADE")
        
        print("Inserting new ICD data...")
        insert_query = """
            INSERT INTO ontology.icd
            (code, title, definition, version, parent_code, chapter, section, full_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        root_records = [r for r in records if r[4] is None]
        cur.executemany(insert_query, root_records)
        conn.commit()
        print(f"Inserted {len(root_records)} root records")
        
        remaining_records = [r for r in records if r[4] is not None]
        inserted_count = len(root_records)
        
        while remaining_records:
            batch_inserted = []
            
            for record in remaining_records[:]:
                parent_code = record[4]
                
                cur.execute("SELECT 1 FROM ontology.icd WHERE code = %s", (parent_code,))
                if cur.fetchone():
                    try:
                        cur.execute(insert_query, record)
                        batch_inserted.append(record)
                        remaining_records.remove(record)
                    except psycopg2.Error as e:
                        print(f"Error inserting {record[0]}: {e}")
            
            if batch_inserted:
                conn.commit()
                inserted_count += len(batch_inserted)
                print(f"Inserted batch of {len(batch_inserted)} records (total: {inserted_count})")
            else:
                print(f"Warning: Could not insert {len(remaining_records)} records due to missing parents")
                break
        
        print(f"✅ Successfully loaded {inserted_count} ICD-10-CM codes into ontology.icd table")
        
        cur.execute("SELECT COUNT(*) FROM ontology.icd")
        total_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM ontology.icd WHERE parent_code IS NULL")
        root_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(DISTINCT parent_code) FROM ontology.icd WHERE parent_code IS NOT NULL")
        parent_count = cur.fetchone()[0]
        
        print(f"\nDatabase Statistics:")
        print(f"Total codes: {total_count}")
        print(f"Root codes: {root_count}")
        print(f"Unique parent codes: {parent_count}")
        
    except Exception as e:
        print(f"Error during database operations: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    default_file = "/home/ubuntu/attachments/0ef2b1b6-946d-4feb-bf2d-ab7d86c39f55/icd10cm-order-April-2025.txt"
    
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_file
    load_icd10cm_data(file_path)
