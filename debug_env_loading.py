#!/usr/bin/env python3
"""
Debug script to check .env loading and file paths
"""
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, '.env')

print(f"Project root: {project_root}")
print(f"Env file path: {env_path}")
print(f"Env file exists: {os.path.exists(env_path)}")

load_dotenv(env_path)

print(f"\nEnvironment variables after loading:")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
print(f"ICD10_MAIN_CODES_FILE: {os.getenv('ICD10_MAIN_CODES_FILE')}")
print(f"ICD10_ADDENDA_FILE: {os.getenv('ICD10_ADDENDA_FILE')}")

project_data_dir = os.path.join(project_root, "server", "data", "icd10")
main_codes_file = os.path.join(project_data_dir, "icd10cm-codes-2026.txt")
addenda_file = os.path.join(project_data_dir, "icd10cm-codes-addenda-2026.txt")

print(f"\nFile path checks:")
print(f"Project data dir: {project_data_dir}")
print(f"Project data dir exists: {os.path.exists(project_data_dir)}")
print(f"Main codes file: {main_codes_file}")
print(f"Main codes file exists: {os.path.exists(main_codes_file)}")
print(f"Addenda file: {addenda_file}")
print(f"Addenda file exists: {os.path.exists(addenda_file)}")

docs_dir = os.path.expanduser("~/Documents/2ndOpinionMD-data")
docs_main = os.path.join(docs_dir, "icd10cm-codes-2026.txt")
docs_addenda = os.path.join(docs_dir, "icd10cm-codes-addenda-2026.txt")

print(f"\nDocuments directory checks:")
print(f"Docs dir: {docs_dir}")
print(f"Docs dir exists: {os.path.exists(docs_dir)}")
print(f"Docs main file exists: {os.path.exists(docs_main)}")
print(f"Docs addenda file exists: {os.path.exists(docs_addenda)}")
