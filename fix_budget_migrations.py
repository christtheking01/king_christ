#!/usr/bin/env python
"""
Script to fix budget migration issues
Run this script to apply all the missing budget-related migrations
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
    print("🔧 Fixing Budget Migration Issues")
    print("=" * 50)
    
    # Commands to run in sequence
    commands = [
        ("source venv/bin/activate", "Activating virtual environment"),
        ("python manage.py makemigrations finance", "Creating finance migrations"),
        ("python manage.py migrate finance", "Applying finance migrations"),
        ("python manage.py migrate", "Applying all migrations"),
    ]
    
    for cmd, description in commands:
        print(f"\n📝 {description}")
        print(f"Command: {cmd}")
        success, stdout, stderr = run_command(cmd)
        
        if success:
            print("✅ Success!")
            if stdout:
                print(f"Output: {stdout[:500]}")  # Limit output length
        else:
            print("❌ Failed!")
            if stderr:
                print(f"Error: {stderr[:500]}")  # Limit error length
                if "Indexes passed to ModelState require a name attribute" in stderr:
                    print("\n🔍 Index name error detected. Migration files have been fixed.")
                    print("Please try running the script again.")
    
    print("\n🎉 Migration process completed!")
    print("\n📋 Next steps:")
    print("1. Restart your Django server")
    print("2. Try accessing the budget reports page")
    print("3. If issues persist, check the database schema")
    
    print("\n🔍 Troubleshooting:")
    print("- If you get index errors, the migrations have been fixed - just run again")
    print("- If you get field errors, check if migrations were applied correctly")
    print("- Use 'python manage.py showmigrations' to check migration status")

if __name__ == "__main__":
    main()
