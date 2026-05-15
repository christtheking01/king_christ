"""
Management command to unblock users locked by security middleware.
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
import hashlib


class Command(BaseCommand):
    help = 'Unblock a user account or IP address from security lockout'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to unblock (account lockout)',
        )
        parser.add_argument(
            '--ip',
            type=str,
            help='IP address to unblock (IP ban/rate limit)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clear all security blocks (use with caution)',
        )

    def handle(self, *args, **options):
        if options['all']:
            # Clear all security-related cache keys
            # Note: This only works with Redis (delete_pattern)
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern('security:*')
                self.stdout.write(self.style.SUCCESS('All security blocks cleared'))
            else:
                self.stdout.write(self.style.ERROR('delete_pattern not available with current cache backend'))
            return

        if options['username']:
            username = options['username'].lower()
            cache.delete(f"security:account_lockout:{username}")
            cache.delete(f"security:account_failures:{username}")
            self.stdout.write(self.style.SUCCESS(f'User "{username}" unblocked'))

        if options['ip']:
            ip = options['ip']
            ip_hash = hashlib.sha256(ip.encode()).hexdigest()
            cache.delete(f"security:blocked_ip:{ip_hash}")
            cache.delete(f"security:ip_failures:{ip_hash}")
            cache.delete(f"security:rate_limit:{ip_hash}")
            self.stdout.write(self.style.SUCCESS(f'IP "{ip}" unblocked'))

        if not any([options['username'], options['ip'], options['all']]):
            self.stdout.write(self.style.WARNING('Provide --username, --ip, or --all'))
