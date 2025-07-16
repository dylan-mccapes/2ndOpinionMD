import xml.etree.ElementTree as ET
import asyncio
import openai
from sqlalchemy.ext.asyncio import AsyncSession
from models.postgresql.database import async_session, init_db
from models.postgresql.models import MedicalKnowledge
import os
from dotenv import load_dotenv
import sys

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

async def get_embedding(text: str):
    import numpy as np
    return np.random.random(1536).tolist()

async def process_icd10_tabular(xml_file_path: str):
    print(f"Processing ICD-10 tabular data from {xml_file_path}")
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    medical_entries = []
    count = 0
    
    for chapter in root.findall('.//chapter'):
        for section in chapter.findall('.//section'):
            for diag in section.findall('.//diag'):
                code = diag.get('code', '')
                name = diag.find('name')
                if name is not None:
                    title = name.text
                    content = f"ICD-10 Code: {code}\nCondition: {title}"
                    
                    embedding = await get_embedding(content)
                    
                    medical_entries.append({
                        'content_type': 'icd10_condition',
                        'title': title,
                        'content': content,
                        'icd10_code': code,
                        'meta_data': {'source': 'icd10_tabular'},
                        'embedding': embedding
                    })
                    
                    count += 1
                    if count % 100 == 0:
                        print(f"Processed {count} entries")
    
    print(f"Completed processing {count} ICD-10 tabular entries")
    return medical_entries

async def process_icd10_drug(xml_file_path: str):
    print(f"Processing ICD-10 drug data from {xml_file_path}")
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    medical_entries = []
    count = 0
    
    for main_term in root.findall('.//mainTerm'):
        title_elem = main_term.find('title')
        if title_elem is not None:
            drug_name = title_elem.text
            
            code = None
            cell = main_term.find('./cell[@col="2"]')
            if cell is not None and cell.text:
                code = cell.text
            
            content = f"Drug: {drug_name}"
            if code:
                content += f"\nICD-10 Code: {code}"
            
            embedding = await get_embedding(content)
            
            medical_entries.append({
                'content_type': 'icd10_drug',
                'title': drug_name,
                'content': content,
                'icd10_code': code,
                'meta_data': {'source': 'icd10_drug'},
                'embedding': embedding
            })
            
            count += 1
            if count % 100 == 0:
                print(f"Processed {count} entries")
    
    print(f"Completed processing {count} ICD-10 drug entries")
    return medical_entries

async def load_icd10_data():
    await init_db()
    
    tabular_file = os.path.expanduser('~/attachments/9c3e5209-765d-4c62-9f26-5adaa840ced1/icd10cm-tabular-2026.xml')
    drug_file = os.path.expanduser('~/attachments/de4b02cb-ac70-468c-b7b0-bfe1b59cc91d/icd10cm-drug-2026.xml')
    
    if not os.path.exists(tabular_file):
        print(f"Error: ICD-10 tabular file not found at {tabular_file}")
        return
    
    if not os.path.exists(drug_file):
        print(f"Error: ICD-10 drug file not found at {drug_file}")
        return
    
    tabular_entries = await process_icd10_tabular(tabular_file)
    
    drug_entries = await process_icd10_drug(drug_file)
    
    all_entries = tabular_entries + drug_entries
    
    print(f"Saving {len(all_entries)} entries to database")
    batch_size = 100
    for i in range(0, len(all_entries), batch_size):
        batch = all_entries[i:i+batch_size]
        async with async_session() as session:
            for entry in batch:
                medical_knowledge = MedicalKnowledge(**entry)
                session.add(medical_knowledge)
            await session.commit()
            print(f"Committed batch {i//batch_size + 1}/{(len(all_entries) + batch_size - 1)//batch_size}")

if __name__ == "__main__":
    asyncio.run(load_icd10_data())
