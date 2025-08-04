#!/usr/bin/env python3
"""
Test script to verify FastAPI app can be imported successfully
"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from server.api.app_postgres import app
    print('✅ FastAPI app imported successfully')
    print(f'✅ App type: {type(app)}')
    print(f'✅ App title: {getattr(app, "title", "N/A")}')
except Exception as e:
    print(f'❌ FastAPI import failed: {e}')
    import traceback
    traceback.print_exc()
