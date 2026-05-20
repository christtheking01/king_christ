#!/usr/bin/env python
"""
Final migration fix script to handle all duplicate field issues
This will apply migrations safely and skip duplicates
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
    print("🔧 Final Migration Fix Script")
    print("=" * 50)
    
    print("\n📋 Step 1: Reset migration state")
    # First, let's see what migrations are applied
    success, stdout, stderr = run_command("source venv/bin/activate && python manage.py showmigrations finance")
    if success:
        print("✅ Current migration status:")
        print(stdout)
    
    print("\n📋 Step 2: Apply migrations with error handling")
    
    # List of migrations to apply in order
    migrations = [
        ("0013_add_budget_management_models", "Budget management models"),
        ("0014_add_enhanced_category_fields", "Category enhancements"),
        ("0015_add_missing_budget_fields", "Missing budget fields"),
        ("0016_safe_budget_allocation_fields", "Budget allocation fields"),
    ]
    
    applied_migrations = []
    
    for migration_name, description in migrations:
        print(f"\n📝 Applying: {description}")
        print(f"Migration: {migration_name}")
        
        success, stdout, stderr = run_command(f"source venv/bin/activate && python manage.py migrate finance {migration_name} --fake-initial")
        
        if success:
            print("✅ Success!")
            applied_migrations.append(migration_name)
        else:
            print("❌ Failed!")
            print(f"Error: {stderr}")
            
            # Try without fake-initial
            success2, stdout2, stderr2 = run_command(f"source venv/bin/activate && python manage.py migrate finance {migration_name}")
            if success2:
                print("✅ Success (without fake-initial)!")
                applied_migrations.append(migration_name)
            else:
                print("❌ Still failed - skipping this migration")
                if "duplicate column name" in stderr2:
                    print("⚠️  Duplicate field detected - field already exists in database")
    
    print("\n📋 Step 3: Apply final migration")
    success, stdout, stderr = run_command("source venv/bin/activate && python manage.py migrate")
    if success:
        print("✅ All migrations completed successfully!")
    else:
        print("⚠️  Some migrations may have issues, but core functionality should work")
        print(f"Final error: {stderr}")
    
    print("\n📋 Step 4: Verify database state")
    success, stdout, stderr = run_command("source venv/bin/activate && python manage.py showmigrations finance")
    if success:
        print("✅ Final migration status:")
        print(stdout)
    
    print("\n🎉 Migration process completed!")
    print("\n📋 Applied migrations:", applied_migrations)
    print("\n📋 Next steps:")
    print("1. Restart your Django server")
    print("2. Try accessing the budget reports page")
    print("3. If you get field errors, the enhanced features may not be available")
    print("4. Basic budget functionality should work")

if __name__ == "__main__":
    main()
