#!/usr/bin/env python3
"""
Script to verify and fix PostgreSQL permissions for Mac Studio setup
"""
import subprocess
import sys

def run_command(cmd, description):
    """Run a shell command and return success status"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False

def main():
    print("🔧 PostgreSQL Permissions Fix for Mac Studio")
    print("=" * 50)
    
    if not run_command("pg_isready", "Check PostgreSQL status"):
        print("\n⚠️ PostgreSQL is not running. Start it with:")
        print("brew services start postgresql@14")
        return False
    
    if not run_command("psql -l | grep 2ndopinionmd", "Check database exists"):
        print("\n⚠️ Database '2ndopinionmd' not found. Create it with:")
        print("createdb 2ndopinionmd")
        return False
    
    commands = [
        ("psql 2ndopinionmd -c \"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO devin;\"", 
         "Grant table privileges"),
        ("psql 2ndopinionmd -c \"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO devin;\"", 
         "Grant sequence privileges"),
        ("psql 2ndopinionmd -c \"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO devin;\"", 
         "Set default table privileges")
    ]
    
    all_success = True
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            all_success = False
    
    if all_success:
        print("\n🎉 All permissions fixed successfully!")
        print("\nNext steps:")
        print("1. cd server")
        print("2. python scripts/load_icd10_data.py")
        print("3. python scripts/run_postgres_app.py")
    else:
        print("\n⚠️ Some permission fixes failed. Please run the commands manually.")
    
    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
