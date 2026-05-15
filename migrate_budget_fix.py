#!/usr/bin/env python
"""
Script to handle budget migration issues step by step
This will help resolve the duplicate field error
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
    print("🔧 Budget Migration Fix Script")
    print("=" * 50)
    
    print("\n📋 Step 1: Checking current migration status")
    success, stdout, stderr = run_command("source venv/bin/activate && python manage.py showmigrations finance")
    if success:
        print("✅ Migration status:")
        print(stdout)
    else:
        print("❌ Failed to check migration status")
        print(stderr)
    
    print("\n📋 Step 2: Applying migrations one by one")
    
    # Apply migrations in order, skipping problematic ones
    migrations_to_apply = [
        ("0012_add_enhanced_budget_allocation_fields", "Budget allocation enhancements"),
        ("0013_add_budget_management_models", "New budget management models"),
        ("0014_add_enhanced_category_fields", "Category enhancements"),
        ("0015_add_missing_budget_fields", "Missing budget fields"),
    ]
    
    for migration_name, description in migrations_to_apply:
        print(f"\n📝 Applying: {description}")
        print(f"Migration: {migration_name}")
        
        success, stdout, stderr = run_command(f"source venv/bin/activate && python manage.py migrate finance {migration_name}")
        
        if success:
            print("✅ Success!")
        else:
            print("❌ Failed!")
            print(f"Error: {stderr}")
            
            # If it's a duplicate field error, try to continue
            if "duplicate column name" in stderr:
                print("⚠️  Duplicate field detected - this field may already exist")
                print("🔄 Continuing with next migration...")
                continue
    
    print("\n📋 Step 3: Final migration check")
    success, stdout, stderr = run_command("source venv/bin/activate && python manage.py migrate")
    if success:
        print("✅ All migrations applied successfully!")
    else:
        print("❌ Some migrations failed")
        print(f"Error: {stderr}")
    
    print("\n🎉 Migration process completed!")
    print("\n📋 Next steps:")
    print("1. Restart your Django server")
    print("2. Try accessing the budget reports page")
    print("3. If you still get field errors, the database may need manual cleanup")

if __name__ == "__main__":
    main()
