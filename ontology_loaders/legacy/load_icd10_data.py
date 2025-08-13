import asyncio
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession
import os
from dotenv import load_dotenv
import sys
import re

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

server_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(server_dir)
sys.path.insert(0, parent_dir)

from models.postgresql.database import async_session, init_db
from models.postgresql.models import MedicalKnowledge
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_embedding(text: str):
    import numpy as np
    return np.random.random(1536).tolist()

async def process_icd10_main_codes(txt_file_path: str):
    print(f"Processing ICD-10 main codes from {txt_file_path}")
    
    medical_entries = []
    count = 0
    
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip('\r\n')
            if not line.strip():
                continue
            
            code_match = re.match(r'^([A-Z0-9]+)\s+(.+)$', line)
            if code_match:
                code = code_match.group(1).strip()
                description = code_match.group(2).strip()
                
                if code and description:
                    content = f"ICD-10 Code: {code}\nCondition: {description}"
                    embedding = await get_embedding(content)
                    
                    medical_entries.append({
                        'content_type': 'icd10_condition',
                        'title': description,
                        'content': content,
                        'icd10_code': code,
                        'meta_data': {'source': 'icd10_main_codes', 'line_number': line_num},
                        'embedding': embedding
                    })
                    
                    count += 1
                    if count % 1000 == 0:
                        print(f"Processed {count} main code entries")
                else:
                    print(f"Warning: Empty code or description at line {line_num}: '{line}'")
            else:
                print(f"Warning: Could not parse line {line_num}: '{line[:50]}...'")
    
    print(f"Completed processing {count} ICD-10 main code entries")
    return medical_entries

async def process_icd10_addenda(txt_file_path: str):
    print(f"Processing ICD-10 addenda from {txt_file_path}")
    
    medical_entries = []
    count = 0
    
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip('\r\n')
            if not line.strip():
                continue
            
            if line.startswith('Add:'):
                action = 'Add'
                rest = line[4:].strip()
            elif line.startswith('Delete:'):
                action = 'Delete'
                rest = line[7:].strip()
            else:
                continue
            
            if action == 'Add':
                parts = rest.split(None, 1)
                if len(parts) >= 2:
                    code = parts[0].strip()
                    description = parts[1].strip()
                    
                    content = f"ICD-10 Code: {code}\nCondition: {description}"
                    embedding = await get_embedding(content)
                    
                    medical_entries.append({
                        'content_type': 'icd10_condition',
                        'title': description,
                        'content': content,
                        'icd10_code': code,
                        'meta_data': {'source': 'icd10_addenda', 'action': action, 'line_number': line_num},
                        'embedding': embedding
                    })
                    
                    count += 1
                    if count % 100 == 0:
                        print(f"Processed {count} addenda entries")
    
    print(f"Completed processing {count} ICD-10 addenda entries")
    return medical_entries

async def load_icd10_data():
    await init_db()
    
    print(f"DEBUG: ICD10_MAIN_CODES_FILE env var: {os.getenv('ICD10_MAIN_CODES_FILE')}")
    print(f"DEBUG: ICD10_ADDENDA_FILE env var: {os.getenv('ICD10_ADDENDA_FILE')}")
    print(f"DEBUG: Project root: {project_root}")
    
    project_data_dir = os.path.join(project_root, "server", "data", "icd10")
    main_codes_file = os.path.join(project_data_dir, "icd10cm-codes-2026.txt")
    addenda_file = os.path.join(project_data_dir, "icd10cm-codes-addenda-2026.txt")
    
    if not os.path.exists(main_codes_file):
        env_main_file = os.getenv("ICD10_MAIN_CODES_FILE")
        if env_main_file and os.path.exists(os.path.expanduser(env_main_file)):
            main_codes_file = os.path.expanduser(env_main_file)
        else:
            docs_main_file = os.path.expanduser("~/Documents/2ndOpinionMD-data/icd10cm-codes-2026.txt")
            if os.path.exists(docs_main_file):
                main_codes_file = docs_main_file
    
    if not os.path.exists(addenda_file):
        env_addenda_file = os.getenv("ICD10_ADDENDA_FILE")
        if env_addenda_file and os.path.exists(os.path.expanduser(env_addenda_file)):
            addenda_file = os.path.expanduser(env_addenda_file)
        else:
            docs_addenda_file = os.path.expanduser("~/Documents/2ndOpinionMD-data/icd10cm-codes-addenda-2026.txt")
            if os.path.exists(docs_addenda_file):
                addenda_file = docs_addenda_file
    
    print(f"DEBUG: Final main_codes_file path: {main_codes_file}")
    print(f"DEBUG: Final addenda_file path: {addenda_file}")
    print(f"DEBUG: Main file exists: {os.path.exists(main_codes_file)}")
    print(f"DEBUG: Addenda file exists: {os.path.exists(addenda_file)}")
    
    if not os.path.exists(main_codes_file):
        print(f"Error: ICD-10 main codes file not found at {main_codes_file}")
        print("Please ensure the file exists at one of these locations:")
        print(f"  1. {os.path.join(project_root, 'server', 'data', 'icd10', 'icd10cm-codes-2026.txt')} (project directory)")
        print(f"  2. {os.getenv('ICD10_MAIN_CODES_FILE', 'Set ICD10_MAIN_CODES_FILE environment variable')}")
        print(f"  3. ~/Documents/2ndOpinionMD-data/icd10cm-codes-2026.txt")
        return
    
    if not os.path.exists(addenda_file):
        print(f"Warning: ICD-10 addenda file not found at {addenda_file}")
        addenda_file = None
    
    main_entries = await process_icd10_main_codes(main_codes_file)
    
    addenda_entries = []
    if addenda_file:
        addenda_entries = await process_icd10_addenda(addenda_file)
    
    all_entries = main_entries + addenda_entries
    
    print(f"Saving {len(all_entries)} total entries to database")
    batch_size = 500
    for i in range(0, len(all_entries), batch_size):
        batch = all_entries[i:i+batch_size]
        async with async_session() as session:
            for entry in batch:
                medical_knowledge = MedicalKnowledge(**entry)
                session.add(medical_knowledge)
            await session.commit()
            print(f"Committed batch {i//batch_size + 1}/{(len(all_entries) + batch_size - 1)//batch_size}")
    
    print(f"Successfully loaded {len(all_entries)} ICD-10 entries into PostgreSQL")

if __name__ == "__main__":
    asyncio.run(load_icd10_data())
