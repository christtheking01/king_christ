from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Sum
from datetime import timedelta, date
from decimal import Decimal

from tithe.models import TithePayment
from finance.models import Transaction
from member.models import Member
from catechesis.models import CatechesisMember, SacramentRequest, Enrollment


class Command(BaseCommand):
    help = 'Send automatic analytics reports to priests and other designated recipients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recipients',
            type=str,
            help='Comma-separated list of email addresses to send report to',
        )
        parser.add_argument(
            '--roles',
            type=str,
            help='Comma-separated list of user roles to send report to (e.g., priest,admin)',
        )
        parser.add_argument(
            '--period',
            type=str,
            default='week',
            choices=['day', 'week', 'month', 'quarter'],
            help='Time period for the report (default: week)',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Send test report without saving',
        )

    def handle(self, *args, **options):
        period = options['period']
        recipients = []
        
        # Calculate date range based on period
        end_date = timezone.now().date()
        if period == 'day':
            start_date = end_date - timedelta(days=1)
        elif period == 'week':
            start_date = end_date - timedelta(weeks=1)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'quarter':
            start_date = end_date - timedelta(days=90)
        
        # Get recipients
        if options.get('recipients'):
            recipients = [email.strip() for email in options['recipients'].split(',')]
        elif options.get('roles'):
            roles = [role.strip() for role in options['roles'].split(',')]
            users = User.objects.filter(roles__in=roles, is_active=True, is_deleted=False)
            recipients = [user.email for user in users if user.email]
        else:
            # Default: send to priests and admins
            users = User.objects.filter(
                roles__in=['priest', 'admin'],
                is_active=True,
                is_deleted=False
            )
            recipients = [user.email for user in users if user.email]
        
        if not recipients:
            self.stdout.write(self.style.WARNING('No recipients found. Use --recipients or --roles'))
            return
        
        # Generate report data
        report_data = self.generate_report_data(start_date, end_date)
        
        # Send email reports
        sent_count = 0
        failed_count = 0
        
        for recipient in recipients:
            try:
                subject = f"Church Analytics Report - {period.capitalize()} ({start_date} to {end_date})"
                
                # Render email content
                message = render_to_string('analytics/email_report.html', {
                    'report_data': report_data,
                    'start_date': start_date,
                    'end_date': end_date,
                    'period': period,
                })
                
                # Send email
                send_mail(
                    subject,
                    '',  # Plain text version (use HTML only)
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient],
                    html_message=message,
                    fail_silently=False,
                )
                
                sent_count += 1
                self.stdout.write(self.style.SUCCESS(f'Report sent to {recipient}'))
                
            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f'Failed to send to {recipient}: {str(e)}'))
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Report Period: {period} ({start_date} to {end_date})')
        self.stdout.write(f'Total Recipients: {len(recipients)}')
        self.stdout.write(f'Successfully Sent: {sent_count}')
        self.stdout.write(f'Failed: {failed_count}')
        self.stdout.write('='*50)
        
        if not options.get('test'):
            # Log the report sending
            self.log_report_sending(recipients, sent_count, failed_count, period, start_date, end_date)

    def generate_report_data(self, start_date, end_date):
        """Generate analytics report data"""
        
        # Tithe data
        total_tithes = TithePayment.objects.filter(
            date__range=[start_date, end_date]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        tithe_count = TithePayment.objects.filter(
            date__range=[start_date, end_date]
        ).count()
        
        # Finance data
        total_income = Transaction.objects.filter(
            date__range=[start_date, end_date],
            type='Income',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        total_expense = Transaction.objects.filter(
            date__range=[start_date, end_date],
            type='Expense',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Member data
        total_members = Member.objects.filter(active=True).count()
        new_members = Member.objects.filter(
            created_at__range=[start_date, end_date]
        ).count() if hasattr(Member, 'created_at') else 0
        
        # Catechesis data
        total_catechesis_members = CatechesisMember.objects.filter(is_deleted=False).count()
        pending_sacraments = SacramentRequest.objects.filter(
            status='pending',
            is_deleted=False
        ).count()
        completed_sacraments = SacramentRequest.objects.filter(
            status='completed',
            completion_date__range=[start_date, end_date],
            is_deleted=False
        ).count()
        
        active_enrollments = Enrollment.objects.filter(
            status='ENROLLED'
        ).count()
        
        return {
            'tithe': {
                'total_amount': total_tithes,
                'count': tithe_count,
                'average': total_tithes / tithe_count if tithe_count > 0 else Decimal('0'),
            },
            'finance': {
                'total_income': total_income,
                'total_expense': total_expense,
                'net': total_income - total_expense,
            },
            'members': {
                'total': total_members,
                'new': new_members,
            },
            'catechesis': {
                'total_members': total_catechesis_members,
                'pending_sacraments': pending_sacraments,
                'completed_sacraments': completed_sacraments,
                'active_enrollments': active_enrollments,
            },
        }

    def log_report_sending(self, recipients, sent_count, failed_count, period, start_date, end_date):
        """Log the report sending for audit purposes"""
        from analytics.models import AnalyticsCache
        
        log_key = f'analytics_report_log_{timezone.now().strftime("%Y%m%d_%H%M%S")}'
        log_data = {
            'recipients': recipients,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'period': period,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'sent_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        try:
            AnalyticsCache.objects.create(
                key=log_key,
                data=log_data,
                expires_at=timezone.now() + timedelta(days=90)
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Failed to log report: {str(e)}'))
