#!/usr/bin/env python3
"""
Verification script for Mac Studio PostgreSQL setup
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def check_env_file():
    """Check if .env file has correct DATABASE_URL for localhost"""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        print("❌ .env file not found in project root")
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    if "DATABASE_URL=postgresql+asyncpg://devin:devin123@2ndopinionmd.ai:5432/2ndopinionmd" in content:
        print("✅ DATABASE_URL correctly configured for 2ndopinionmd.ai server")
        return True
    elif "DATABASE_URL=" in content:
        print("⚠️ DATABASE_URL found but not configured for 2ndopinionmd.ai server")
        print("   Expected: DATABASE_URL=postgresql+asyncpg://devin:devin123@2ndopinionmd.ai:5432/2ndopinionmd")
        return False
    else:
        print("❌ DATABASE_URL not found in .env file")
        return False

def check_icd10_files():
    """Check if ICD-10 data files are available"""
    locations = [
        "~/Documents/2ndOpinionMD-data/icd10cm-codes-2026.txt",
        str(REPO_ROOT / "server/data/icd10/icd10cm-codes-2026.txt"),
    ]
    
    found = False
    for location in locations:
        path = Path(location).expanduser()
        if path.exists():
            print(f"✅ ICD-10 main codes file found at: {path}")
            found = True
            break
    
    if not found:
        print("❌ ICD-10 main codes file not found at any expected location:")
        for location in locations:
            print(f"   - {location}")
        return False
    
    return True

def check_database_connection():
    """Test database connection"""
    try:
        import asyncpg
        import asyncio
        
        async def test_connection():
            try:
                conn = await asyncpg.connect(
                    "postgresql://devin:devin123@2ndopinionmd.ai:5432/2ndopinionmd"
                )
                await conn.close()
                return True
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                return False
        
        result = asyncio.run(test_connection())
        if result:
            print("✅ PostgreSQL database connection successful")
        return result
        
    except ImportError:
        print("⚠️ asyncpg not installed - cannot test database connection")
        print("   Run: pip install asyncpg")
        return False

def main():
    print("🔍 Verifying Mac Studio PostgreSQL Setup\n")
    
    checks = [
        ("Environment Configuration", check_env_file),
        ("ICD-10 Data Files", check_icd10_files),
        ("Database Connection", check_database_connection)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"Checking {name}...")
        if not check_func():
            all_passed = False
        print()
    
    if all_passed:
        print("🎉 All checks passed! Your Mac Studio setup is ready.")
        print("\nNext steps:")
        print("1. cd server")
        print("2. python scripts/load_icd10_data.py")
        print("3. python scripts/run_postgres_app.py")
    else:
        print("⚠️ Some checks failed. Please address the issues above.")
        print("\nFirst, make sure PostgreSQL is running:")
        print("brew services start postgresql@14")
        print("\nIf you just pulled the latest changes, try running:")
        print("git pull origin devin/1752707339-postgresql-icd10-migration")

if __name__ == "__main__":
    main()
