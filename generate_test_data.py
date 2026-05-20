#!/usr/bin/env python3
"""
Simplified Finance Test Data Generator
Run with: python generate_test_data.py
"""

import os
import sys
import django
from datetime import datetime, timedelta, date
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'christ_king_church.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from finance.models import (
    Category, Transaction, TitheReceipt, Offering, Employee, Payroll,
    Budget, BudgetAllocation, BudgetVariance, BudgetPeriod, BudgetAlert,
    ExpenseReport, ExpenseItem, EventPledge, PledgePayment
)
from member.models import Member
from events.models import Event
from users.models import User

User = get_user_model()


def clear_existing_data():
    """Clear existing test data"""
    print("Clearing existing test data...")
    models_to_clear = [
        PledgePayment, EventPledge, ExpenseItem, ExpenseReport,
        BudgetAlert, BudgetPeriod, BudgetVariance, BudgetAllocation, Budget,
        Payroll, Employee, Offering, TitheReceipt, Transaction, Category
    ]
    
    for model in models_to_clear:
        try:
            count = model.objects.count()
            model.objects.all().delete()
            print(f"Cleared {count} {model.__name__} records")
        except Exception as e:
            print(f"Error clearing {model.__name__}: {e}")


def create_admin_user():
    """Create admin user"""
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@christkingchurch.com',
            'firstname': 'System',
            'lastname': 'Administrator',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        user.set_password('admin123')
        user.save()
        print("Created admin user: admin/admin123")
    return user


def create_members():
    """Create realistic church members"""
    members_data = [
        {'name': 'John Mwangi', 'code': 'CKC001', 'phone': '+255712345001', 'gender': 'male'},
        {'name': 'Mary Wanjiku', 'code': 'CKC002', 'phone': '+255712345002', 'gender': 'female'},
        {'name': 'Peter Ochieng', 'code': 'CKC003', 'phone': '+255712345003', 'gender': 'male'},
        {'name': 'Grace Achieng', 'code': 'CKC004', 'phone': '+255712345004', 'gender': 'female'},
        {'name': 'James Kamau', 'code': 'CKC005', 'phone': '+255712345005', 'gender': 'male'},
        {'name': 'Sarah Njeri', 'code': 'CKC006', 'phone': '+255712345006', 'gender': 'female'},
        {'name': 'David Kipchoge', 'code': 'CKC007', 'phone': '+255712345007', 'gender': 'male'},
        {'name': 'Elizabeth Wakesho', 'code': 'CKC008', 'phone': '+255712345008', 'gender': 'female'},
        {'name': 'Joseph Mutua', 'code': 'CKC009', 'phone': '+255712345009', 'gender': 'male'},
        {'name': 'Ann Muthoni', 'code': 'CKC010', 'phone': '+255712345010', 'gender': 'female'},
        {'name': 'Michael Njoroge', 'code': 'CKC011', 'phone': '+255712345011', 'gender': 'male'},
        {'name': 'Rose Wambui', 'code': 'CKC012', 'phone': '+255712345012', 'gender': 'female'},
        {'name': 'Daniel Kiprop', 'code': 'CKC013', 'phone': '+255712345013', 'gender': 'male'},
        {'name': 'Faith Chebet', 'code': 'CKC014', 'phone': '+255712345014', 'gender': 'female'},
        {'name': 'Samuel Langat', 'code': 'CKC015', 'phone': '+255712345015', 'gender': 'male'},
    ]

    members = []
    for data in members_data:
        member, created = Member.objects.get_or_create(
            code=data['code'],
            defaults={
                'name': data['name'],
                'telephone': data['phone'],
                'gender': data['gender'],
                'active': True,
                'pays_tithe': True,
                'working': True
            }
        )
        members.append(member)
        if created:
            print(f"Created member: {member.name}")

    return members


def create_categories(user):
    """Create comprehensive financial categories"""
    categories_data = [
        # Income Categories
        {'name': 'Sunday Collection', 'type': 'INCOME', 'subcategory': 'OFFERING', 'description': 'Weekly Sunday service offerings'},
        {'name': 'Special Collection', 'type': 'INCOME', 'subcategory': 'OFFERING', 'description': 'Special occasion collections'},
        {'name': 'Tithe Payments', 'type': 'INCOME', 'subcategory': 'TITHE', 'description': 'Monthly tithe collections from members'},
        {'name': 'Building Fund', 'type': 'INCOME', 'subcategory': 'OFFERING', 'description': 'Contributions for church building projects'},
        {'name': 'Mission Donations', 'type': 'INCOME', 'subcategory': 'DONATIONS', 'description': 'Donations for missionary work'},

        # Expense Categories
        {'name': 'Priest Salary', 'type': 'EXPENSE', 'subcategory': 'SALARIES', 'description': 'Monthly salary for parish priest'},
        {'name': 'Secretary Salary', 'type': 'EXPENSE', 'subcategory': 'SALARIES', 'description': 'Monthly salary for church secretary'},
        {'name': 'Accountant Salary', 'type': 'EXPENSE', 'subcategory': 'SALARIES', 'description': 'Monthly salary for church accountant'},
        {'name': 'Caretaker Salary', 'type': 'EXPENSE', 'subcategory': 'SALARIES', 'description': 'Monthly salary for church caretaker'},
        {'name': 'Choir Director Salary', 'type': 'EXPENSE', 'subcategory': 'SALARIES', 'description': 'Monthly salary for choir director'},

        {'name': 'Electricity Bill', 'type': 'EXPENSE', 'subcategory': 'UTILITIES', 'description': 'Monthly electricity consumption'},
        {'name': 'Water Bill', 'type': 'EXPENSE', 'subcategory': 'UTILITIES', 'description': 'Monthly water consumption'},
        {'name': 'Internet Bill', 'type': 'EXPENSE', 'subcategory': 'UTILITIES', 'description': 'Monthly internet services'},
        {'name': 'Telephone Bill', 'type': 'EXPENSE', 'subcategory': 'UTILITIES', 'description': 'Monthly telephone services'},

        {'name': 'Building Maintenance', 'type': 'EXPENSE', 'subcategory': 'MAINTENANCE', 'description': 'Repairs and upkeep of church building'},
        {'name': 'Equipment Maintenance', 'type': 'EXPENSE', 'subcategory': 'MAINTENANCE', 'description': 'Maintenance of church equipment'},
        {'name': 'Vehicle Maintenance', 'type': 'EXPENSE', 'subcategory': 'MAINTENANCE', 'description': 'Maintenance of church vehicles'},

        {'name': 'Mission Outreach', 'type': 'EXPENSE', 'subcategory': 'MISSIONS', 'description': 'Support for missionary activities'},
        {'name': 'Charity Programs', 'type': 'EXPENSE', 'subcategory': 'MISSIONS', 'description': 'Support for local charity programs'},
        {'name': 'Youth Programs', 'type': 'EXPENSE', 'subcategory': 'PROGRAMS', 'description': 'Youth ministry activities'},

        {'name': 'Christmas Celebration', 'type': 'EXPENSE', 'subcategory': 'PROGRAMS', 'description': 'Annual Christmas celebration expenses'},
        {'name': 'Easter Celebration', 'type': 'EXPENSE', 'subcategory': 'PROGRAMS', 'description': 'Annual Easter celebration expenses'},
        {'name': 'Wedding Services', 'type': 'EXPENSE', 'subcategory': 'PROGRAMS', 'description': 'Church wedding service fees'},
        {'name': 'Funeral Services', 'type': 'EXPENSE', 'subcategory': 'PROGRAMS', 'description': 'Church funeral service fees'},

        {'name': 'Office Supplies', 'type': 'EXPENSE', 'subcategory': 'OFFICE_SUPPLIES', 'description': 'Administrative office supplies'},
        {'name': 'Cleaning Supplies', 'type': 'EXPENSE', 'subcategory': 'OFFICE_SUPPLIES', 'description': 'Cleaning and maintenance supplies'},
        {'name': 'Religious Materials', 'type': 'EXPENSE', 'subcategory': 'OFFICE_SUPPLIES', 'description': 'Bibles, hymnals, and religious materials'},
    ]

    categories = []
    for data in categories_data:
        category, created = Category.objects.get_or_create(
            user=user,
            name=data['name'],
            type=data['type'],
            defaults={
                'subcategory': data['subcategory'],
                'description': data['description']
            }
        )
        categories.append(category)
        if created:
            print(f"Created category: {category.name}")

    return categories


def create_recent_transactions(user, categories):
    """Create realistic recent transactions for the last 3 months"""
    today = timezone.now().date()

    # Income transactions (last 12 weeks)
    income_data = [
        {'category': 'Sunday Collection', 'amount': 280000, 'desc': 'Sunday Collection - First Service', 'weeks_ago': 0},
        {'category': 'Sunday Collection', 'amount': 195000, 'desc': 'Sunday Collection - Second Service', 'weeks_ago': 0},
        {'category': 'Sunday Collection', 'amount': 320000, 'desc': 'Sunday Collection - First Service', 'weeks_ago': 1},
        {'category': 'Sunday Collection', 'amount': 245000, 'desc': 'Sunday Collection - Second Service', 'weeks_ago': 1},
        {'category': 'Sunday Collection', 'amount': 290000, 'desc': 'Sunday Collection - First Service', 'weeks_ago': 2},
        {'category': 'Sunday Collection', 'amount': 210000, 'desc': 'Sunday Collection - Second Service', 'weeks_ago': 2},
        {'category': 'Tithe Payments', 'amount': 850000, 'desc': 'February tithe collections', 'weeks_ago': 2},
        {'category': 'Tithe Payments', 'amount': 920000, 'desc': 'January tithe collections', 'weeks_ago': 6},
        {'category': 'Building Fund', 'amount': 150000, 'desc': 'Building fund special collection', 'weeks_ago': 1},
        {'category': 'Mission Donations', 'amount': 75000, 'desc': 'Mission support collection', 'weeks_ago': 3},
        {'category': 'Special Collection', 'amount': 200000, 'desc': 'Thanksgiving special collection', 'weeks_ago': 4},
    ]

    # Expense transactions (last 12 weeks)
    expense_data = [
        {'category': 'Priest Salary', 'amount': 800000, 'desc': 'February priest salary', 'weeks_ago': 1},
        {'category': 'Secretary Salary', 'amount': 450000, 'desc': 'February secretary salary', 'weeks_ago': 1},
        {'category': 'Accountant Salary', 'amount': 600000, 'desc': 'February accountant salary', 'weeks_ago': 1},
        {'category': 'Caretaker Salary', 'amount': 300000, 'desc': 'February caretaker salary', 'weeks_ago': 1},
        {'category': 'Electricity Bill', 'amount': 185000, 'desc': 'February electricity bill', 'weeks_ago': 2},
        {'category': 'Water Bill', 'amount': 45000, 'desc': 'February water bill', 'weeks_ago': 2},
        {'category': 'Internet Bill', 'amount': 35000, 'desc': 'February internet bill', 'weeks_ago': 2},
        {'category': 'Building Maintenance', 'amount': 125000, 'desc': 'Roof repairs and painting', 'weeks_ago': 3},
        {'category': 'Office Supplies', 'amount': 45000, 'desc': 'Office stationery and supplies', 'weeks_ago': 4},
        {'category': 'Mission Outreach', 'amount': 200000, 'desc': 'Missionary support payment', 'weeks_ago': 5},
        {'category': 'Cleaning Supplies', 'amount': 25000, 'desc': 'Monthly cleaning supplies', 'weeks_ago': 6},
        {'category': 'Religious Materials', 'amount': 75000, 'desc': 'New hymnals and bibles', 'weeks_ago': 7},
    ]

    transactions_created = 0

    # Create income transactions
    for data in income_data:
        category = next((c for c in categories if c.name == data['category']), None)
        if category:
            transaction_date = today - timedelta(weeks=data['weeks_ago'])
            Transaction.objects.get_or_create(
                user=user,
                category=category,
                amount=data['amount'],
                date=transaction_date,
                defaults={
                    'type': 'Income',
                    'description': data['desc'],
                    'status': 'COMPLETED',
                    'reference_number': f"INC-{transaction_date.strftime('%Y%m%d')}-{transactions_created+1:03d}"
                }
            )
            transactions_created += 1

    # Create expense transactions
    for data in expense_data:
        category = next((c for c in categories if c.name == data['category']), None)
        if category:
            transaction_date = today - timedelta(weeks=data['weeks_ago'])
            Transaction.objects.get_or_create(
                user=user,
                category=category,
                amount=data['amount'],
                date=transaction_date,
                defaults={
                    'type': 'Expense',
                    'description': data['desc'],
                    'status': 'COMPLETED',
                    'reference_number': f"EXP-{transaction_date.strftime('%Y%m%d')}-{transactions_created+1:03d}"
                }
            )
            transactions_created += 1

    print(f"Created {transactions_created} recent transactions")


def create_tithe_receipts(user, members):
    """Create recent tithe payment receipts"""
    today = timezone.now().date()

    tithe_data = [
        {'member': members[0], 'amount': 50000, 'method': 'cash', 'days_ago': 5},
        {'member': members[1], 'amount': 75000, 'method': 'bank', 'days_ago': 3},
        {'member': members[2], 'amount': 60000, 'method': 'mobile', 'days_ago': 7},
        {'member': members[3], 'amount': 80000, 'method': 'cash', 'days_ago': 10},
        {'member': members[4], 'amount': 45000, 'method': 'bank', 'days_ago': 12},
        {'member': members[5], 'amount': 90000, 'method': 'cash', 'days_ago': 8},
        {'member': members[6], 'amount': 55000, 'method': 'mobile', 'days_ago': 6},
        {'member': members[7], 'amount': 70000, 'method': 'bank', 'days_ago': 4},
        {'member': members[8], 'amount': 40000, 'method': 'cash', 'days_ago': 9},
        {'member': members[9], 'amount': 85000, 'method': 'mobile', 'days_ago': 2},
        {'member': members[10], 'amount': 65000, 'method': 'cash', 'days_ago': 1},
        {'member': members[11], 'amount': 95000, 'method': 'bank', 'days_ago': 11},
    ]

    for i, data in enumerate(tithe_data):
        payment_date = today - timedelta(days=data['days_ago'])
        TitheReceipt.objects.get_or_create(
            user=user,
            member=data['member'],
            amount=data['amount'],
            date=payment_date,
            defaults={
                'payment_method': data['method'],
                'receipt_number': f"RCT-{payment_date.strftime('%Y%m%d')}-{i+1:03d}",
                'notes': f"Monthly tithe payment from {data['member'].name}"
            }
        )

    print(f"Created {len(tithe_data)} tithe receipts")


def create_offerings(user, members):
    """Create recent offering records"""
    today = timezone.now().date()

    offerings_data = [
        {'type': 'SUNDAY', 'amount': 25000, 'method': 'CASH', 'anonymous': True, 'days_ago': 0},
        {'type': 'SUNDAY', 'amount': 50000, 'method': 'CASH', 'member': members[4], 'days_ago': 0},
        {'type': 'SPECIAL', 'amount': 100000, 'method': 'MOBILE', 'member': members[3], 'days_ago': 7},
        {'type': 'BUILDING', 'amount': 150000, 'method': 'BANK', 'member': members[1], 'days_ago': 14},
        {'type': 'MISSIONS', 'amount': 75000, 'method': 'CASH', 'anonymous': True, 'days_ago': 21},
        {'type': 'SUNDAY', 'amount': 30000, 'method': 'MOBILE', 'member': members[6], 'days_ago': 7},
        {'type': 'THANKSGIVING', 'amount': 200000, 'method': 'BANK', 'member': members[2], 'days_ago': 28},
        {'type': 'SUNDAY', 'amount': 45000, 'method': 'CASH', 'member': members[8], 'days_ago': 14},
        {'type': 'SPECIAL', 'amount': 80000, 'method': 'MOBILE', 'anonymous': True, 'days_ago': 21},
        {'type': 'BUILDING', 'amount': 120000, 'method': 'BANK', 'member': members[5], 'days_ago': 35},
    ]

    for i, data in enumerate(offerings_data):
        offering_date = today - timedelta(days=data['days_ago'])
        is_anonymous = data.get('anonymous', False)
        member = data.get('member') if not is_anonymous else None

        Offering.objects.get_or_create(
            user=user,
            offering_type=data['type'],
            date=offering_date,
            amount=data['amount'],
            defaults={
                'payment_method': data['method'],
                'donor_name': None if is_anonymous else (member.name if member else f"Visitor {i+1}"),
                'donor_phone': None if is_anonymous else (member.telephone if member else f"+255712345{i+100:03d}"),
                'is_anonymous': is_anonymous,
                'member': member,
                'receipt_number': f"OFF-{offering_date.strftime('%Y%m%d')}-{i+1:03d}",
                'notes': f"{data['type'].title()} offering collection"
            }
        )

    print(f"Created {len(offerings_data)} offerings")


def create_employees(user, members):
    """Create church employees"""
    employees_data = [
        {'member': members[0], 'id': 'EMP001', 'position': 'Parish Priest', 'base': 800000, 'hire_days': 365*2},
        {'member': members[1], 'id': 'EMP002', 'position': 'Secretary', 'base': 450000, 'hire_days': 365*1},
        {'member': members[2], 'id': 'EMP003', 'position': 'Accountant', 'base': 600000, 'hire_days': 365*1},
        {'member': members[3], 'id': 'EMP004', 'position': 'Caretaker', 'base': 300000, 'hire_days': 365*0.5},
        {'member': members[4], 'id': 'EMP005', 'position': 'Choir Director', 'base': 250000, 'hire_days': 365*0.8},
    ]

    employees = []
    for data in employees_data:
        hire_date = timezone.now().date() - timedelta(days=int(data['hire_days']))

        employee, created = Employee.objects.get_or_create(
            employee_id=data['id'],
            defaults={
                'user': user,
                'name': data['member'].name,
                'position': data['position'],
                'department': 'Church Administration' if data['position'] in ['Parish Priest', 'Secretary', 'Accountant'] else 'Support Services',
                'base_salary': data['base'],
                'payment_type': 'MONTHLY',
                'bank_account': f"123456789{data['id'][-1]}",
                'bank_name': 'CRDB Bank',
                'tax_id': f"TAX{data['id'][-3:]}",
                'status': 'ACTIVE',
                'hire_date': hire_date
            }
        )
        employees.append(employee)
        if created:
            print(f"Created employee: {employee.name} - {employee.position}")

    return employees


def create_payrolls(user, employees):
    """Create recent payroll records"""
    today = timezone.now().date()

    # Create payroll for last 3 months
    for months_ago in range(3):
        pay_date = today.replace(day=1) - timedelta(days=months_ago*30)

        for employee in employees:
            pay_period_end = pay_date + timedelta(days=29)

            Payroll.objects.get_or_create(
                employee=employee,
                pay_period_start=pay_date,
                pay_period_end=pay_period_end,
                defaults={
                    'user': user,
                    'basic_salary': employee.base_salary,
                    'gross_salary': employee.base_salary,
                    'tax_deduction': employee.base_salary * Decimal('0.15'),
                    'other_deductions': 0,
                    'net_salary': employee.base_salary * Decimal('0.85'),
                    'status': 'PAID',
                    'payment_date': pay_period_end,
                    'notes': f"Monthly salary payment for {pay_date.strftime('%B %Y')}"
                }
            )

    print(f"Created payroll records for {len(employees)} employees (3 months each)")


def create_budgets(user, categories):
    """Create current and upcoming budgets"""
    today = timezone.now().date()

    budgets_data = [
        {
            'name': '2024 Annual Budget',
            'total': 18000000,
            'start': today.replace(month=1, day=1),
            'end': today.replace(month=12, day=31),
            'status': 'ACTIVE',
            'allocations': [
                ('Priest Salary', 9600000),
                ('Secretary Salary', 5400000),
                ('Accountant Salary', 7200000),
                ('Caretaker Salary', 3600000),
                ('Electricity Bill', 2400000),
                ('Water Bill', 600000),
                ('Building Maintenance', 1800000),
                ('Mission Outreach', 1200000),
                ('Christmas Celebration', 600000),
                ('Office Supplies', 300000),
            ]
        },
        {
            'name': 'Q1 2024 Events Budget',
            'total': 2500000,
            'start': today.replace(month=1, day=1),
            'end': today.replace(month=3, day=31),
            'status': 'ACTIVE',
            'allocations': [
                ('Christmas Celebration', 1500000),
                ('Easter Celebration', 1000000),
            ]
        },
    ]

    for budget_data in budgets_data:
        budget, created = Budget.objects.get_or_create(
            user=user,
            name=budget_data['name'],
            defaults={
                'description': f"Budget for {budget_data['name']}",
                'total_amount': budget_data['total'],
                'start_date': budget_data['start'],
                'end_date': budget_data['end'],
                'status': budget_data['status'],
                'approved_by': user,
                'approved_at': today - timedelta(days=30)
            }
        )

        if created:
            total_allocated = 0
            for cat_name, amount in budget_data['allocations']:
                category = next((c for c in categories if cat_name in c.name), None)
                if category:
                    spent_amount = amount * Decimal('0.5')
                    BudgetAllocation.objects.create(
                        budget=budget,
                        category=category,
                        allocated_amount=amount,
                        spent_amount=spent_amount
                    )
                    total_allocated += amount

            print(f"Created budget: {budget.name} (Total: {budget.total_amount:,} TZS)")


def create_expense_reports(user, employees, categories):
    """Create expense reports for testing"""
    today = timezone.now().date()

    expense_reports_data = [
        {
            'title': 'Pastoral Visit Expenses - February 2024',
            'employee': employees[0],
            'amount': 125000,
            'status': 'APPROVED',
            'items': [
                {'category': 'Mission Outreach', 'desc': 'Transport and accommodation', 'amount': 125000}
            ]
        },
        {
            'title': 'Office Supplies - January 2024',
            'employee': employees[1],
            'amount': 65000,
            'status': 'REIMBURSED',
            'items': [
                {'category': 'Office Supplies', 'desc': 'Stationery and printing', 'amount': 45000},
                {'category': 'Cleaning Supplies', 'desc': 'Cleaning materials', 'amount': 20000}
            ]
        },
        {
            'title': 'Choir Practice Materials',
            'employee': employees[4],
            'amount': 45000,
            'status': 'PENDING',
            'items': [
                {'category': 'Religious Materials', 'desc': 'Music sheets and materials', 'amount': 45000}
            ]
        },
    ]

    for data in expense_reports_data:
        report, created = ExpenseReport.objects.get_or_create(
            user=user,
            title=data['title'],
            defaults={
                'employee': data['employee'],
                'description': f"Expense report for {data['title'].lower()}",
                'total_amount': data['amount'],
                'date_submitted': today - timedelta(days=10),
                'status': data['status'],
                'approved_by': user if data['status'] in ['APPROVED', 'REIMBURSED'] else None,
                'date_approved': today - timedelta(days=5) if data['status'] in ['APPROVED', 'REIMBURSED'] else None,
                'notes': f"Submitted by {data['employee'].name}"
            }
        )

        if created:
            for item_data in data['items']:
                category = next((c for c in categories if c.name == item_data['category']), None)
                if category:
                    ExpenseItem.objects.create(
                        expense_report=report,
                        category=category,
                        description=item_data['desc'],
                        amount=item_data['amount'],
                        date_incurred=today - timedelta(days=15),
                        receipt_number=f"RCP-{1000 + len(data['items'])}"
                    )

            print(f"Created expense report: {report.title}")


def main():
    """Main function to generate comprehensive test data"""
    print("=" * 70)
    print("FINANCE TEST DATA GENERATOR")
    print("=" * 70)
    print()

    with transaction.atomic():
        # Create base data
        admin = create_admin_user()
        members = create_members()
        categories = create_categories(admin)

        # Create financial records
        create_recent_transactions(admin, categories)
        create_tithe_receipts(admin, members)
        create_offerings(admin, members)

        # Create employee and payroll data
        employees = create_employees(admin, members)
        create_payrolls(admin, employees)

        # Create budgets and expenses
        create_budgets(admin, categories)
        create_expense_reports(admin, employees, categories)

    print("\n" + "=" * 70)
    print("TEST DATA GENERATION COMPLETED!")
    print("=" * 70)

    # Print summary
    print("\n📊 DATA SUMMARY:")
    print(f"   👥 Members: {Member.objects.count()}")
    print(f"   📂 Categories: {Category.objects.count()}")
    print(f"   💰 Transactions: {Transaction.objects.count()}")
    print(f"   🧾 Tithe Receipts: {TitheReceipt.objects.count()}")
    print(f"   🙏 Offerings: {Offering.objects.count()}")
    print(f"   👷 Employees: {Employee.objects.count()}")
    print(f"   💵 Payroll Records: {Payroll.objects.count()}")
    print(f"   📊 Budgets: {Budget.objects.count()}")
    print(f"   📋 Expense Reports: {ExpenseReport.objects.count()}")

    print("\n🔐 LOGIN CREDENTIALS:")
    print("   Username: admin")
    print("   Password: admin123")


if __name__ == '__main__':
    main()
