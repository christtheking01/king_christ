#!/usr/bin/env python3
"""
Financial App Test Data Generator
Run with: python manage.py shell < finance_test_data.py
Or: python manage.py runscript finance_test_data (if using django-extensions)
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'christ_king_church.settings')
sys.path.append('/media/emmanuel-leonard/NewVolume/Projects/testing /Kristo_mfalme')
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


def create_superuser():
    """Create admin user if not exists"""
    if not User.objects.filter(username='admin').exists():
        user = User.objects.create_superuser(
            username='admin',
            email='admin@christkingchurch.com',
            password='admin123',
            first_name='System',
            last_name='Administrator'
        )
        print(f"Created superuser: {user.username}")
        return user
    return User.objects.get(username='admin')


def create_test_members():
    """Create test members if none exist"""
    members_data = [
        {'name': 'John Mwangi', 'member_id': 'CKC001', 'telephone': '+255712345001', 'gender': 'Male'},
        {'name': 'Mary Wanjiku', 'member_id': 'CKC002', 'telephone': '+255712345002', 'gender': 'Female'},
        {'name': 'Peter Ochieng', 'member_id': 'CKC003', 'telephone': '+255712345003', 'gender': 'Male'},
        {'name': 'Grace Achieng', 'member_id': 'CKC004', 'telephone': '+255712345004', 'gender': 'Female'},
        {'name': 'James Kamau', 'member_id': 'CKC005', 'telephone': '+255712345005', 'gender': 'Male'},
        {'name': 'Sarah Njeri', 'member_id': 'CKC006', 'telephone': '+255712345006', 'gender': 'Female'},
        {'name': 'David Kipchoge', 'member_id': 'CKC007', 'telephone': '+255712345007', 'gender': 'Male'},
        {'name': 'Elizabeth Wakesho', 'member_id': 'CKC008', 'telephone': '+255712345008', 'gender': 'Female'},
        {'name': 'Joseph Mutua', 'member_id': 'CKC009', 'telephone': '+255712345009', 'gender': 'Male'},
        {'name': 'Ann Muthoni', 'member_id': 'CKC010', 'telephone': '+255712345010', 'gender': 'Female'},
    ]
    
    members = []
    for data in members_data:
        member, created = Member.objects.get_or_create(
            member_id=data['member_id'],
            defaults={
                'name': data['name'],
                'telephone': data['telephone'],
                'gender': data['gender'],
                'baptised': True,
                'confirmed': True
            }
        )
        members.append(member)
        if created:
            print(f"Created member: {member.name}")
    
    return members


def create_categories(user):
    """Create financial categories"""
    categories_data = [
        {'name': 'Sunday Collection', 'type': 'OFFERING', 'description': 'Weekly Sunday offerings'},
        {'name': 'Tithe Payments', 'type': 'TITHE', 'description': 'Monthly tithe collections'},
        {'name': 'Priest Salary', 'type': 'SALARY', 'description': 'Monthly priest salary'},
        {'name': 'Secretary Salary', 'type': 'SALARY', 'description': 'Church secretary salary'},
        {'name': 'Electricity Bill', 'type': 'UTILITIES', 'description': 'Monthly electricity'},
        {'name': 'Water Bill', 'type': 'UTILITIES', 'description': 'Monthly water bill'},
        {'name': 'Building Maintenance', 'type': 'MAINTENANCE', 'description': 'Repairs and upkeep'},
        {'name': 'Mission Outreach', 'type': 'MISSIONS', 'description': 'Missionary support'},
        {'name': 'Christmas Event', 'type': 'EVENTS', 'description': 'Christmas celebration'},
        {'name': 'Easter Event', 'type': 'EVENTS', 'description': 'Easter celebrations'},
    ]
    
    categories = []
    for data in categories_data:
        cat, created = Category.objects.get_or_create(
            user=user,
            name=data['name'],
            defaults={
                'type': data['type'],
                'description': data['description']
            }
        )
        categories.append(cat)
        if created:
            print(f"Created category: {cat.name}")
    
    return categories


def create_transactions(user, categories):
    """Create sample income and expense transactions"""
    transactions_data = [
        # Income transactions
        {'category': 'Sunday Collection', 'type': 'Income', 'amount': 150000, 'description': 'Sunday collection - First Service', 'date': timezone.now().date() - timedelta(days=7)},
        {'category': 'Sunday Collection', 'type': 'Income', 'amount': 125000, 'description': 'Sunday collection - Second Service', 'date': timezone.now().date() - timedelta(days=7)},
        {'category': 'Tithe Payments', 'type': 'Income', 'amount': 350000, 'description': 'January tithe collections', 'date': timezone.now().date() - timedelta(days=15)},
        {'category': 'Sunday Collection', 'type': 'Income', 'amount': 180000, 'description': 'Sunday collection - First Service', 'date': timezone.now().date() - timedelta(days=14)},
        {'category': 'Sunday Collection', 'type': 'Income', 'amount': 140000, 'description': 'Sunday collection - Second Service', 'date': timezone.now().date() - timedelta(days=14)},
        
        # Expense transactions
        {'category': 'Priest Salary', 'type': 'Expense', 'amount': 800000, 'description': 'January priest salary', 'date': timezone.now().date() - timedelta(days=5)},
        {'category': 'Secretary Salary', 'type': 'Expense', 'amount': 450000, 'description': 'January secretary salary', 'date': timezone.now().date() - timedelta(days=5)},
        {'category': 'Electricity Bill', 'type': 'Expense', 'amount': 185000, 'description': 'January electricity', 'date': timezone.now().date() - timedelta(days=3)},
        {'category': 'Water Bill', 'type': 'Expense', 'amount': 45000, 'description': 'January water bill', 'date': timezone.now().date() - timedelta(days=3)},
        {'category': 'Building Maintenance', 'type': 'Expense', 'amount': 125000, 'description': 'Roof repairs', 'date': timezone.now().date() - timedelta(days=10)},
        {'category': 'Mission Outreach', 'type': 'Expense', 'amount': 200000, 'description': 'Missionary support payment', 'date': timezone.now().date() - timedelta(days=8)},
    ]
    
    for data in transactions_data:
        category = next((c for c in categories if c.name == data['category']), None)
        if category:
            Transaction.objects.get_or_create(
                user=user,
                category=category,
                amount=data['amount'],
                date=data['date'],
                defaults={
                    'type': data['type'],
                    'description': data['description'],
                    'status': 'COMPLETED'
                }
            )
    print(f"Created {len(transactions_data)} transactions")


def create_tithe_receipts(user, members):
    """Create tithe payment receipts"""
    tithe_data = [
        {'member': members[0], 'amount': 50000, 'payment_method': 'cash', 'date': timezone.now() - timedelta(days=5)},
        {'member': members[1], 'amount': 75000, 'payment_method': 'bank', 'date': timezone.now() - timedelta(days=3)},
        {'member': members[2], 'amount': 60000, 'payment_method': 'mobile', 'date': timezone.now() - timedelta(days=7)},
        {'member': members[3], 'amount': 80000, 'payment_method': 'cash', 'date': timezone.now() - timedelta(days=10)},
        {'member': members[4], 'amount': 45000, 'payment_method': 'bank', 'date': timezone.now() - timedelta(days=12)},
        {'member': members[5], 'amount': 90000, 'payment_method': 'cash', 'date': timezone.now() - timedelta(days=8)},
        {'member': members[6], 'amount': 55000, 'payment_method': 'mobile', 'date': timezone.now() - timedelta(days=6)},
        {'member': members[7], 'amount': 70000, 'payment_method': 'bank', 'date': timezone.now() - timedelta(days=4)},
        {'member': members[8], 'amount': 40000, 'payment_method': 'cash', 'date': timezone.now() - timedelta(days=9)},
        {'member': members[9], 'amount': 85000, 'payment_method': 'mobile', 'date': timezone.now() - timedelta(days=2)},
    ]
    
    for data in tithe_data:
        TitheReceipt.objects.create(
            user=user,
            member=data['member'],
            amount=data['amount'],
            payment_method=data['payment_method'],
            date=data['date'],
            notes=f"Monthly tithe from {data['member'].name}"
        )
    print(f"Created {len(tithe_data)} tithe receipts")


def create_offerings(user, members):
    """Create offering records"""
    offering_types = ['SUNDAY', 'SPECIAL', 'THANKSGIVING', 'BUILDING', 'MISSIONS', 'CHARITY']
    payment_methods = ['CASH', 'BANK', 'MOBILE', 'CHEQUE']
    
    for i in range(25):
        is_anonymous = random.choice([True, False])
        member = random.choice(members) if not is_anonymous else None
        
        Offering.objects.create(
            user=user,
            offering_type=random.choice(offering_types),
            date=timezone.now().date() - timedelta(days=random.randint(1, 30)),
            amount=random.choice([5000, 10000, 15000, 20000, 25000, 50000, 100000]),
            payment_method=random.choice(payment_methods),
            donor_name=None if is_anonymous else (member.name if member else f"Donor {i+1}"),
            donor_phone=None if is_anonymous else f"+255712345{random.randint(100, 999)}",
            is_anonymous=is_anonymous,
            member=None if is_anonymous else member,
            notes=f"Offering collection #{i+1}"
        )
    
    print(f"Created 25 offerings")


def create_employees(user, members):
    """Create employee records"""
    positions = [
        {'position': 'Parish Priest', 'base': 800000, 'housing': 200000, 'transport': 100000},
        {'position': 'Secretary', 'base': 450000, 'housing': 100000, 'transport': 50000},
        {'position': 'Accountant', 'base': 600000, 'housing': 150000, 'transport': 75000},
        {'position': 'Caretaker', 'base': 300000, 'housing': 50000, 'transport': 50000},
        {'position': 'Choir Director', 'base': 250000, 'housing': 0, 'transport': 25000},
    ]
    
    employees = []
    for i, pos_data in enumerate(positions):
        if i < len(members):
            emp, created = Employee.objects.get_or_create(
                member=members[i],
                defaults={
                    'user': user,
                    'employee_id': f'EMP{i+1:03d}',
                    'position': pos_data['position'],
                    'department': 'Church Administration' if i < 3 else 'Support Services',
                    'base_salary': pos_data['base'],
                    'housing_allowance': pos_data['housing'],
                    'transport_allowance': pos_data['transport'],
                    'hire_date': timezone.now().date() - timedelta(days=random.randint(365, 1825)),
                    'status': 'ACTIVE'
                }
            )
            employees.append(emp)
            if created:
                print(f"Created employee: {emp.member.name} - {emp.position}")
    
    return employees


def create_payrolls(user, employees):
    """Create payroll records"""
    for employee in employees:
        for month in range(1, 4):  # Last 3 months
            pay_date = timezone.now().date().replace(month=month, day=1)
            
            Payroll.objects.get_or_create(
                employee=employee,
                pay_period_start=pay_date,
                pay_period_end=pay_date + timedelta(days=29),
                defaults={
                    'user': user,
                    'basic_salary': employee.base_salary,
                    'housing_allowance': employee.housing_allowance,
                    'transport_allowance': employee.transport_allowance,
                    'other_allowances': employee.other_allowances,
                    'gross_salary': employee.total_salary,
                    'tax_deduction': employee.total_salary * Decimal('0.15'),
                    'other_deductions': 0,
                    'net_salary': employee.total_salary * Decimal('0.85'),
                    'status': 'PAID',
                    'payment_date': pay_date + timedelta(days=29)
                }
            )
    print(f"Created payroll records for {len(employees)} employees (3 months each)")


def create_budgets(user, categories):
    """Create budget records"""
    budgets_data = [
        {
            'name': '2024 Annual Budget',
            'total': 15000000,
            'start': timezone.now().date().replace(month=1, day=1),
            'end': timezone.now().date().replace(month=12, day=31),
            'status': 'ACTIVE',
            'allocations': [
                ('Priest Salary', 9600000),
                ('Utilities', 2400000),
                ('Maintenance', 1200000),
                ('Missions', 1200000),
                ('Events', 600000),
            ]
        },
        {
            'name': 'Q1 2024 Events',
            'total': 2000000,
            'start': timezone.now().date().replace(month=1, day=1),
            'end': timezone.now().date().replace(month=3, day=31),
            'status': 'COMPLETED',
            'allocations': [
                ('Christmas Event', 800000),
                ('Easter Event', 1200000),
            ]
        },
    ]
    
    for budget_data in budgets_data:
        budget, created = Budget.objects.get_or_create(
            user=user,
            name=budget_data['name'],
            defaults={
                'total_amount': budget_data['total'],
                'start_date': budget_data['start'],
                'end_date': budget_data['end'],
                'status': budget_data['status']
            }
        )
        
        if created:
            for cat_name, amount in budget_data['allocations']:
                category = next((c for c in categories if cat_name in c.name), None)
                if category:
                    BudgetAllocation.objects.create(
                        budget=budget,
                        category=category,
                        allocated_amount=amount,
                        spent_amount=amount * Decimal(str(random.uniform(0.3, 0.8)))
                    )
            print(f"Created budget: {budget.name}")


def create_expense_reports(user, employees, categories):
    """Create expense reports"""
    expense_data = [
        {'title': 'Pastoral Visit Expenses', 'amount': 75000, 'status': 'REIMBURSED'},
        {'title': 'Office Supplies', 'amount': 45000, 'status': 'APPROVED'},
        {'title': 'Choir Practice Materials', 'amount': 30000, 'status': 'PENDING'},
        {'title': 'Transport for Mission', 'amount': 120000, 'status': 'REIMBURSED'},
        {'title': 'Refreshments for Meeting', 'amount': 25000, 'status': 'APPROVED'},
    ]
    
    for data in expense_data:
        report, created = ExpenseReport.objects.get_or_create(
            user=user,
            title=data['title'],
            defaults={
                'employee': random.choice(employees) if employees else None,
                'description': f"Expense report for {data['title'].lower()}",
                'total_amount': data['amount'],
                'status': data['status'],
                'approved_by': user if data['status'] in ['APPROVED', 'REIMBURSED'] else None,
                'date_approved': timezone.now().date() - timedelta(days=random.randint(1, 10)) if data['status'] in ['APPROVED', 'REIMBURSED'] else None
            }
        )
        
        if created:
            # Add expense items
            ExpenseItem.objects.create(
                expense_report=report,
                category=random.choice([c for c in categories if c.type in ['MAINTENANCE', 'OTHERS', 'EVENTS']]),
                description=f"Main expense for {data['title']}",
                amount=data['amount'],
                date_incurred=timezone.now().date() - timedelta(days=random.randint(5, 20)),
                receipt_number=f"RCP-{random.randint(1000, 9999)}"
            )
            print(f"Created expense report: {report.title}")


def create_events(user):
    """Create test events"""
    events_data = [
        {'title': 'Christmas Carol Service', 'date': timezone.now().date() + timedelta(days=30), 'type': 'RELIGIOUS'},
        {'title': 'Easter Celebration', 'date': timezone.now().date() + timedelta(days=60), 'type': 'RELIGIOUS'},
        {'title': 'Church Building Fundraiser', 'date': timezone.now().date() + timedelta(days=45), 'type': 'FUNDRAISER'},
        {'title': 'Youth Conference', 'date': timezone.now().date() + timedelta(days=90), 'type': 'CONFERENCE'},
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
                'description': f"Annual {data['title']} celebration",
                'is_recurring': False,
                'max_attendees': 500
            }
        )
        events.append(event)
        if created:
            print(f"Created event: {event.title}")
    
    return events


def create_pledges_and_payments(user, events, members):
    """Create event pledges and payments"""
    pledge_statuses = ['PENDING', 'PARTIAL', 'COMPLETED']
    
    for event in events:
        # Create 3-5 pledges per event
        for _ in range(random.randint(3, 5)):
            member = random.choice(members)
            promised = random.choice([50000, 100000, 150000, 200000, 300000])
            
            pledge = EventPledge.objects.create(
                user=user,
                event=event,
                member=member,
                promised_amount=promised,
                paid_amount=0,
                due_date=event.date - timedelta(days=7),
                status='PENDING',
                notes=f"Pledge for {event.title}"
            )
            
            # Add some payments
            if random.choice([True, False]):
                payment_count = random.randint(1, 3)
                total_paid = 0
                
                for _ in range(payment_count):
                    payment_amount = random.choice([10000, 25000, 50000])
                    if total_paid + payment_amount <= promised:
                        PledgePayment.objects.create(
                            pledge=pledge,
                            amount=payment_amount,
                            payment_method=random.choice(['CASH', 'BANK', 'MOBILE']),
                            payment_date=timezone.now().date() - timedelta(days=random.randint(1, 20)),
                            received_by=user,
                            notes=f"Installment payment"
                        )
                        total_paid += payment_amount
                
                # Update pledge
                pledge.paid_amount = total_paid
                pledge.update_status()
    
    print(f"Created pledges and payments for {len(events)} events")


def main():
    """Main function to create all test data"""
    print("=" * 60)
    print("FINANCIAL APP TEST DATA GENERATOR")
    print("=" * 60)
    
    with transaction.atomic():
        # Create base data
        admin = create_superuser()
        members = create_test_members()
        categories = create_categories(admin)
        
        # Create financial records
        create_transactions(admin, categories)
        create_tithe_receipts(admin, members)
        create_offerings(admin, members)
        
        # Create employee data
        employees = create_employees(admin, members)
        create_payrolls(admin, employees)
        
        # Create budgets and expenses
        create_budgets(admin, categories)
        create_expense_reports(admin, employees, categories)
        
        # Create events with pledges
        events = create_events(admin)
        create_pledges_and_payments(admin, events, members)
    
    print("=" * 60)
    print("TEST DATA CREATION COMPLETED!")
    print("=" * 60)
    print("\nSummary:")
    print(f"- Categories: {Category.objects.count()}")
    print(f"- Transactions: {Transaction.objects.count()}")
    print(f"- Tithe Receipts: {TitheReceipt.objects.count()}")
    print(f"- Offerings: {Offering.objects.count()}")
    print(f"- Employees: {Employee.objects.count()}")
    print(f"- Payrolls: {Payroll.objects.count()}")
    print(f"- Budgets: {Budget.objects.count()}")
    print(f"- Expense Reports: {ExpenseReport.objects.count()}")
    print(f"- Events: {Event.objects.count()}")
    print(f"- Event Pledges: {EventPledge.objects.count()}")
    print(f"- Pledge Payments: {PledgePayment.objects.count()}")
    print("\nYou can now log in with:")
    print("  Username: admin")
    print("  Password: admin123")


if __name__ == '__main__':
    main()
