#!/usr/bin/env python
"""
Generate fresh migrations from current models
"""

import os
import sys
import subprocess

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🔄 Fresh Migration Generation")
    print("=" * 40)
    
    print("\n📋 Step 1: Check current migration status")
    success, stdout, stderr = run_command("source venv/bin/activate && python manage.py showmigrations finance")
    if success:
        print("✅ Current migration status:")
        print(stdout)
    
    print("\n📋 Step 2: Generate fresh migrations")
    print("This will create migrations based on current model state...")
    
    success, stdout, stderr = run_command("source venv/bin/activate && python manage.py makemigrations finance")
    
    if success:
        print("✅ Fresh migrations generated successfully!")
        print(stdout)
    else:
        print("❌ Failed to generate migrations")
        print(stderr)
        return
    
    print("\n📋 Step 3: Check what migrations were created")
    success, stdout, stderr = run_command("ls -la /media/emmanuel-leonard/NewVolume/Projects/space/Kristo_mfalme/finance/migrations/*.py | grep -E '00[1-9][0-9]_'")
    if success:
        print("✅ Migration files found:")
        print(stdout)
    
    print("\n📋 Step 4: Apply the fresh migrations")
    success, stdout, stderr = run_command("source venv/bin/activate && python manage.py migrate finance")
    
    if success:
        print("✅ Fresh migrations applied successfully!")
        print(stdout)
    else:
        print("❌ Failed to apply migrations")
        print(stderr)
        return
    
    print("\n📋 Step 5: Final migration status")
    success, stdout, stderr = run_command("source venv/bin/activate && python manage.py showmigrations finance")
    if success:
        print("✅ Final migration status:")
        print(stdout)
    
    print("\n🎉 Fresh migration process completed!")
    print("\n📋 Next steps:")
    print("1. Restart your Django server")
    print("2. Try accessing the budget reports page")
    print("3. The enhanced budget features should now work")

if __name__ == "__main__":
    main()
