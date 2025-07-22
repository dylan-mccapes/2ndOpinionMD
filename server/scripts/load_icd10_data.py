import asyncio
import openai
from sqlalchemy.ext.asyncio import AsyncSession
import os
from dotenv import load_dotenv
import sys
import re

server_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(server_dir)
sys.path.insert(0, parent_dir)

from models.postgresql.database import async_session, init_db
from models.postgresql.models import MedicalKnowledge

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    
    main_codes_file = os.path.expanduser('~/attachments/665dd5b7-20c3-4f73-aabc-666a9bdb8257/icd10cm-codes-2026.txt')
    addenda_file = os.path.expanduser('~/attachments/f5971c19-8f16-4ec7-b2dc-91c6f5b94d3e/icd10cm-codes-addenda-2026.txt')
    
    if not os.path.exists(main_codes_file):
        print(f"Error: ICD-10 main codes file not found at {main_codes_file}")
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
