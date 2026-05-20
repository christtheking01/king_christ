#!/usr/bin/env python3
"""
Comprehensive Finance App Test Data Generator
Generates realistic, current test data for all finance app functionality

Run with: python manage.py shell < comprehensive_finance_test_data.py
"""

import os
import sys
import django
from datetime import datetime, timedelta, date
from decimal import Decimal
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'christ_king_church.settings')
sys.path.append('/media/emmanuel-leonard/NewVolume/Projects/space/Kristo_mfalme')
django.setup()

from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from finance.models import (
    Category, Transaction, TitheReceipt, Offering, Employee, Payroll,
    Budget, BudgetAllocation, ExpenseReport, ExpenseItem, EventPledge, PledgePayment
)
from member.models import Member
from events.models import Event
from users.models import User

User = get_user_model()


def clear_existing_data():
    """Clear existing test data"""
    print("Clearing existing test data...")
    models_to_clear = [
        EventPledge, PledgePayment, ExpenseItem, ExpenseReport,
        BudgetAllocation, Budget, Payroll, Employee,
        Offering, TitheReceipt, Transaction, Category
    ]

    for model in models_to_clear:
        count = model.objects.count()
        model.objects.all().delete()
        print(f"Cleared {count} {model.__name__} records")


def create_admin_user():
    """Create admin user"""
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@christkingchurch.com',
            'first_name': 'System',
            'last_name': 'Administrator',
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
        {'name': 'John Mwangi', 'member_id': 'CKC001', 'phone': '+255712345001', 'gender': 'Male', 'status': 'active'},
        {'name': 'Mary Wanjiku', 'member_id': 'CKC002', 'phone': '+255712345002', 'gender': 'Female', 'status': 'active'},
        {'name': 'Peter Ochieng', 'member_id': 'CKC003', 'phone': '+255712345003', 'gender': 'Male', 'status': 'active'},
        {'name': 'Grace Achieng', 'member_id': 'CKC004', 'phone': '+255712345004', 'gender': 'Female', 'status': 'active'},
        {'name': 'James Kamau', 'member_id': 'CKC005', 'phone': '+255712345005', 'gender': 'Male', 'status': 'active'},
        {'name': 'Sarah Njeri', 'member_id': 'CKC006', 'phone': '+255712345006', 'gender': 'Female', 'status': 'active'},
        {'name': 'David Kipchoge', 'member_id': 'CKC007', 'phone': '+255712345007', 'gender': 'Male', 'status': 'active'},
        {'name': 'Elizabeth Wakesho', 'member_id': 'CKC008', 'phone': '+255712345008', 'gender': 'Female', 'status': 'active'},
        {'name': 'Joseph Mutua', 'member_id': 'CKC009', 'phone': '+255712345009', 'gender': 'Male', 'status': 'active'},
        {'name': 'Ann Muthoni', 'member_id': 'CKC010', 'phone': '+255712345010', 'gender': 'Female', 'status': 'active'},
        {'name': 'Michael Njoroge', 'member_id': 'CKC011', 'phone': '+255712345011', 'gender': 'Male', 'status': 'active'},
        {'name': 'Rose Wambui', 'member_id': 'CKC012', 'phone': '+255712345012', 'gender': 'Female', 'status': 'active'},
        {'name': 'Daniel Kiprop', 'member_id': 'CKC013', 'phone': '+255712345013', 'gender': 'Male', 'status': 'active'},
        {'name': 'Faith Chebet', 'member_id': 'CKC014', 'phone': '+255712345014', 'gender': 'Female', 'status': 'active'},
        {'name': 'Samuel Langat', 'member_id': 'CKC015', 'phone': '+255712345015', 'gender': 'Male', 'status': 'active'},
    ]

    members = []
    for data in members_data:
        member, created = Member.objects.get_or_create(
            member_id=data['member_id'],
            defaults={
                'name': data['name'],
                'telephone': data['phone'],
                'gender': data['gender'],
                'baptised': True,
                'confirmed': True,
                'status': data['status'],
                'join_date': timezone.now().date() - timedelta(days=random.randint(30, 365*3))
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
        {'name': 'Sunday Collection', 'type': 'OFFERING', 'description': 'Weekly Sunday service offerings'},
        {'name': 'Special Collection', 'type': 'OFFERING', 'description': 'Special occasion collections'},
        {'name': 'Tithe Payments', 'type': 'TITHE', 'description': 'Monthly tithe collections from members'},
        {'name': 'Building Fund', 'type': 'OFFERING', 'description': 'Contributions for church building projects'},
        {'name': 'Mission Donations', 'type': 'OFFERING', 'description': 'Donations for missionary work'},

        # Expense Categories
        {'name': 'Priest Salary', 'type': 'SALARY', 'description': 'Monthly salary for parish priest'},
        {'name': 'Secretary Salary', 'type': 'SALARY', 'description': 'Monthly salary for church secretary'},
        {'name': 'Accountant Salary', 'type': 'SALARY', 'description': 'Monthly salary for church accountant'},
        {'name': 'Caretaker Salary', 'type': 'SALARY', 'description': 'Monthly salary for church caretaker'},
        {'name': 'Choir Director Salary', 'type': 'SALARY', 'description': 'Monthly salary for choir director'},

        {'name': 'Electricity Bill', 'type': 'UTILITIES', 'description': 'Monthly electricity consumption'},
        {'name': 'Water Bill', 'type': 'UTILITIES', 'description': 'Monthly water consumption'},
        {'name': 'Internet Bill', 'type': 'UTILITIES', 'description': 'Monthly internet services'},
        {'name': 'Telephone Bill', 'type': 'UTILITIES', 'description': 'Monthly telephone services'},

        {'name': 'Building Maintenance', 'type': 'MAINTENANCE', 'description': 'Repairs and upkeep of church building'},
        {'name': 'Equipment Maintenance', 'type': 'MAINTENANCE', 'description': 'Maintenance of church equipment'},
        {'name': 'Vehicle Maintenance', 'type': 'MAINTENANCE', 'description': 'Maintenance of church vehicles'},

        {'name': 'Mission Outreach', 'type': 'MISSIONS', 'description': 'Support for missionary activities'},
        {'name': 'Charity Programs', 'type': 'MISSIONS', 'description': 'Support for local charity programs'},
        {'name': 'Youth Programs', 'type': 'MISSIONS', 'description': 'Youth ministry activities'},

        {'name': 'Christmas Celebration', 'type': 'EVENTS', 'description': 'Annual Christmas celebration expenses'},
        {'name': 'Easter Celebration', 'type': 'EVENTS', 'description': 'Annual Easter celebration expenses'},
        {'name': 'Wedding Services', 'type': 'EVENTS', 'description': 'Church wedding service fees'},
        {'name': 'Funeral Services', 'type': 'EVENTS', 'description': 'Church funeral service fees'},

        {'name': 'Office Supplies', 'type': 'ADMIN', 'description': 'Administrative office supplies'},
        {'name': 'Cleaning Supplies', 'type': 'ADMIN', 'description': 'Cleaning and maintenance supplies'},
        {'name': 'Religious Materials', 'type': 'ADMIN', 'description': 'Bibles, hymnals, and religious materials'},
    ]

    categories = []
    for data in categories_data:
        category, created = Category.objects.get_or_create(
            user=user,
            name=data['name'],
            defaults={
                'type': data['type'],
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
        # Sunday Collections (every Sunday)
        {'category': 'Sunday Collection', 'amount': 280000, 'desc': 'Sunday Collection - First Service', 'weeks_ago': 0},
        {'category': 'Sunday Collection', 'amount': 195000, 'desc': 'Sunday Collection - Second Service', 'weeks_ago': 0},
        {'category': 'Sunday Collection', 'amount': 320000, 'desc': 'Sunday Collection - First Service', 'weeks_ago': 1},
        {'category': 'Sunday Collection', 'amount': 245000, 'desc': 'Sunday Collection - Second Service', 'weeks_ago': 1},
        {'category': 'Sunday Collection', 'amount': 290000, 'desc': 'Sunday Collection - First Service', 'weeks_ago': 2},
        {'category': 'Sunday Collection', 'amount': 210000, 'desc': 'Sunday Collection - Second Service', 'weeks_ago': 2},

        # Tithe Collections (monthly)
        {'category': 'Tithe Payments', 'amount': 850000, 'desc': 'February tithe collections', 'weeks_ago': 2},
        {'category': 'Tithe Payments', 'amount': 920000, 'desc': 'January tithe collections', 'weeks_ago': 6},

        # Special Collections
        {'category': 'Building Fund', 'amount': 150000, 'desc': 'Building fund special collection', 'weeks_ago': 1},
        {'category': 'Mission Donations', 'amount': 75000, 'desc': 'Mission support collection', 'weeks_ago': 3},
        {'category': 'Special Collection', 'amount': 200000, 'desc': 'Thanksgiving special collection', 'weeks_ago': 4},
    ]

    # Expense transactions (last 12 weeks)
    expense_data = [
        # Salaries (monthly)
        {'category': 'Priest Salary', 'amount': 800000, 'desc': 'February priest salary', 'weeks_ago': 1},
        {'category': 'Secretary Salary', 'amount': 450000, 'desc': 'February secretary salary', 'weeks_ago': 1},
        {'category': 'Accountant Salary', 'amount': 600000, 'desc': 'February accountant salary', 'weeks_ago': 1},
        {'category': 'Caretaker Salary', 'amount': 300000, 'desc': 'February caretaker salary', 'weeks_ago': 1},

        # Utilities (monthly)
        {'category': 'Electricity Bill', 'amount': 185000, 'desc': 'February electricity bill', 'weeks_ago': 2},
        {'category': 'Water Bill', 'amount': 45000, 'desc': 'February water bill', 'weeks_ago': 2},
        {'category': 'Internet Bill', 'amount': 35000, 'desc': 'February internet bill', 'weeks_ago': 2},

        # Maintenance and other expenses
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
    offering_types = ['SUNDAY', 'SPECIAL', 'THANKSGIVING', 'BUILDING', 'MISSIONS']
    payment_methods = ['CASH', 'BANK', 'MOBILE']

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
        {
            'member': members[0], 'id': 'EMP001', 'position': 'Parish Priest',
            'base': 800000, 'housing': 200000, 'transport': 100000, 'hire_days': 365*2
        },
        {
            'member': members[1], 'id': 'EMP002', 'position': 'Secretary',
            'base': 450000, 'housing': 100000, 'transport': 50000, 'hire_days': 365*1.5
        },
        {
            'member': members[2], 'id': 'EMP003', 'position': 'Accountant',
            'base': 600000, 'housing': 150000, 'transport': 75000, 'hire_days': 365*1
        },
        {
            'member': members[3], 'id': 'EMP004', 'position': 'Caretaker',
            'base': 300000, 'housing': 50000, 'transport': 50000, 'hire_days': 365*0.5
        },
        {
            'member': members[4], 'id': 'EMP005', 'position': 'Choir Director',
            'base': 250000, 'housing': 0, 'transport': 25000, 'hire_days': 365*0.8
        },
    ]

    employees = []
    for data in employees_data:
        hire_date = timezone.now().date() - timedelta(days=int(data['hire_days']))

        employee, created = Employee.objects.get_or_create(
            member=data['member'],
            defaults={
                'user': user,
                'employee_id': data['id'],
                'position': data['position'],
                'department': 'Church Administration' if data['position'] in ['Parish Priest', 'Secretary', 'Accountant'] else 'Support Services',
                'base_salary': data['base'],
                'housing_allowance': data['housing'],
                'transport_allowance': data['transport'],
                'other_allowances': 0,
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
            print(f"Created employee: {employee.member.name} - {employee.position}")

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
                    'housing_allowance': employee.housing_allowance,
                    'transport_allowance': employee.transport_allowance,
                    'other_allowances': employee.other_allowances,
                    'gross_salary': employee.total_salary,
                    'tax_deduction': employee.total_salary * Decimal('0.15'),  # 15% tax
                    'other_deductions': 0,
                    'net_salary': employee.total_salary * Decimal('0.85'),
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
            'total': 18000000,  # 18 million TZS
            'start': today.replace(month=1, day=1),
            'end': today.replace(month=12, day=31),
            'status': 'ACTIVE',
            'allocations': [
                ('Priest Salary', 9600000),      # 9.6M for priest salary
                ('Secretary Salary', 5400000),   # 5.4M for secretary
                ('Accountant Salary', 7200000),  # 7.2M for accountant
                ('Caretaker Salary', 3600000),   # 3.6M for caretaker
                ('Electricity Bill', 2400000),   # 2.4M for utilities
                ('Water Bill', 600000),          # 600K for water
                ('Building Maintenance', 1800000), # 1.8M for maintenance
                ('Mission Outreach', 1200000),   # 1.2M for missions
                ('Christmas Celebration', 600000), # 600K for events
                ('Office Supplies', 300000),     # 300K for admin
            ]
        },
        {
            'name': 'Q1 2024 Events Budget',
            'total': 2500000,  # 2.5M for Q1 events
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
                    # Simulate some spending (30-80% of allocation)
                    spent_percentage = random.uniform(0.3, 0.8)
                    spent_amount = amount * Decimal(str(spent_percentage))

                    BudgetAllocation.objects.create(
                        budget=budget,
                        category=category,
                        allocated_amount=amount,
                        spent_amount=spent_amount
                    )
                    total_allocated += amount

            print(f"Created budget: {budget.name} (Total: {budget.total_amount:,} TZS, Allocated: {total_allocated:,} TZS)")


def create_expense_reports(user, employees, categories):
    """Create expense reports for testing"""
    today = timezone.now().date()

    expense_reports_data = [
        {
            'title': 'Pastoral Visit Expenses - February 2024',
            'employee': employees[0],  # Priest
            'amount': 125000,
            'status': 'APPROVED',
            'items': [
                {'category': 'Mission Outreach', 'desc': 'Transport and accommodation', 'amount': 125000}
            ]
        },
        {
            'title': 'Office Supplies - January 2024',
            'employee': employees[1],  # Secretary
            'amount': 65000,
            'status': 'REIMBURSED',
            'items': [
                {'category': 'Office Supplies', 'desc': 'Stationery and printing', 'amount': 45000},
                {'category': 'Cleaning Supplies', 'desc': 'Cleaning materials', 'amount': 20000}
            ]
        },
        {
            'title': 'Choir Practice Materials',
            'employee': employees[4],  # Choir Director
            'amount': 45000,
            'status': 'PENDING',
            'items': [
                {'category': 'Religious Materials', 'desc': 'Music sheets and materials', 'amount': 45000}
            ]
        },
        {
            'title': 'Building Repairs - Roof',
            'employee': employees[3],  # Caretaker
            'amount': 185000,
            'status': 'APPROVED',
            'items': [
                {'category': 'Building Maintenance', 'desc': 'Roof repair materials', 'amount': 185000}
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
                'date_submitted': today - timedelta(days=random.randint(1, 14)),
                'status': data['status'],
                'approved_by': user if data['status'] in ['APPROVED', 'REIMBURSED'] else None,
                'date_approved': today - timedelta(days=random.randint(1, 7)) if data['status'] in ['APPROVED', 'REIMBURSED'] else None,
                'notes': f"Submitted by {data['employee'].member.name}"
            }
        )

        if created:
            # Create expense items
            for item_data in data['items']:
                category = next((c for c in categories if c.name == item_data['category']), None)
                if category:
                    ExpenseItem.objects.create(
                        expense_report=report,
                        category=category,
                        description=item_data['desc'],
                        amount=item_data['amount'],
                        date_incurred=today - timedelta(days=random.randint(5, 20)),
                        receipt_number=f"RCP-{random.randint(1000, 9999)}"
                    )

            print(f"Created expense report: {report.title} ({report.status})")


def create_events_and_pledges(user, members):
    """Create upcoming events with pledges"""
    today = timezone.now().date()

    events_data = [
        {
            'title': 'Easter Celebration 2024',
            'date': today + timedelta(days=45),
            'type': 'RELIGIOUS',
            'description': 'Annual Easter celebration with special services'
        },
        {
            'title': 'Youth Conference 2024',
            'date': today + timedelta(days=75),
            'type': 'CONFERENCE',
            'description': 'Annual youth conference and retreat'
        },
        {
            'title': 'Church Building Fundraiser',
            'date': today + timedelta(days=30),
            'type': 'FUNDRAISER',
            'description': 'Fundraising event for new church building extension'
        },
    ]

    events = []
    for data in events_data:
        event, created = Event.objects.get_or_create(
            title=data['title'],
            defaults={
                'created_by': user,
                'date': data['date'],
                'time': '10:00',
                'location': 'Christ The King Church',
                'event_type': data['type'],
                'description': data['description'],
                'is_recurring': False,
                'max_attendees': 500
            }
        )
        events.append(event)
        if created:
            print(f"Created event: {event.title}")

    # Create pledges for events
    pledge_amounts = [50000, 100000, 150000, 200000, 250000, 300000]

    for event in events:
        # Create 5-8 pledges per event
        pledge_members = random.sample(members, random.randint(5, 8))

        for member in pledge_members:
            promised_amount = random.choice(pledge_amounts)

            pledge = EventPledge.objects.create(
                user=user,
                event=event,
                member=member,
                promised_amount=promised_amount,
                paid_amount=0,
                due_date=event.date - timedelta(days=7),
                status='PENDING',
                notes=f"Pledge for {event.title} by {member.name}"
            )

            # Add some payments (30% chance of having payments)
            if random.random() < 0.3:
                payment_count = random.randint(1, 3)
                total_paid = 0

                for _ in range(payment_count):
                    payment_amount = random.choice([25000, 50000, 75000])
                    if total_paid + payment_amount <= promised_amount:
                        PledgePayment.objects.create(
                            pledge=pledge,
                            amount=payment_amount,
                            payment_method=random.choice(['CASH', 'BANK', 'MOBILE']),
                            payment_date=today - timedelta(days=random.randint(1, 14)),
                            received_by=user,
                            notes=f"Partial payment towards {event.title}"
                        )
                        total_paid += payment_amount

                # Update pledge with payments
                pledge.paid_amount = total_paid
                pledge.update_status()

    print(f"Created pledges and payments for {len(events)} events")


def main():
    """Main function to generate comprehensive test data"""
    print("=" * 70)
    print("COMPREHENSIVE FINANCE APP TEST DATA GENERATOR")
    print("=" * 70)
    print("This will generate realistic, current test data for all finance functionality")
    print()

    # Ask user if they want to clear existing data
    clear_data = input("Clear existing test data? (y/N): ").lower().strip() == 'y'

    with transaction.atomic():
        if clear_data:
            clear_existing_data()

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

        # Create events with pledges
        create_events_and_pledges(admin, members)

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
    print(f"   📅 Events: {Event.objects.count()}")
    print(f"   🤝 Event Pledges: {EventPledge.objects.count()}")
    print(f"   💳 Pledge Payments: {PledgePayment.objects.count()}")

    print("\n🔐 LOGIN CREDENTIALS:")
    print("   Username: admin")
    print("   Password: admin123")

    print("\n🎯 TEST SCENARIOS READY:")
    print("   • Financial dashboard with current data")
    print("   • Transaction management (income/expense)")
    print("   • Budget creation and tracking")
    print("   • Employee payroll processing")
    print("   • Tithe and offering collection")
    print("   • Expense report approval workflow")
    print("   • Event pledge management")
    print("   • Financial reporting and exports")

    print("\n💡 TIPS FOR TESTING:")
    print("   • Check financial dashboard for summary")
    print("   • Test budget allocations and spending")
    print("   • Verify payroll calculations")
    print("   • Test expense report approval process")
    print("   • Check pledge payment tracking")
    print("   • Export financial reports")


if __name__ == '__main__':
    main()