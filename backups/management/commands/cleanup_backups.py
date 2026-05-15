"""
Clean up old backups - Command: python manage.py cleanup_backups
"""

from django.core.management.base import BaseCommand, CommandError
from backups.backup_manager import BackupManager


class Command(BaseCommand):
    help = 'Remove old backups from cloud storage'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete backups older than this many days (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        self.stdout.write(
            f'Scanning for backups older than {days} days...'
        )
        
        try:
            manager = BackupManager()
            backups = manager.list_s3_backups()
            
            # Filter old backups
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            old_backups = [
                b for b in backups 
                if b['last_modified'].replace(tzinfo=None) < cutoff_date
            ]
            
            if not old_backups:
                self.stdout.write(
                    self.style.SUCCESS('No old backups found to clean up.')
                )
                return
            
            self.stdout.write(
                f'Found {len(old_backups)} backups older than {days} days'
            )
            
            if dry_run:
                self.stdout.write(
                    self.style.NOTICE('\\nDry run - the following would be deleted:')
                )
                for backup in old_backups:
                    self.stdout.write(f'  - {backup["key"]}')
                return
            
            # Confirm deletion
            self.stdout.write(
                self.style.WARNING(
                    f'\\nWARNING: This will permanently delete {len(old_backups)} backups!'
                )
            )
            confirm = input('Type "DELETE" to confirm: ')
            
            if confirm != 'DELETE':
                self.stdout.write(self.style.ERROR('Cleanup cancelled.'))
                return
            
            # Perform cleanup
            deleted = manager.cleanup_old_backups(days=days)
            
            self.stdout.write(
                self.style.SUCCESS(f'\\nDeleted {len(deleted)} old backups:')
            )
            for key in deleted:
                self.stdout.write(f'  - {key}')
                
        except Exception as e:
            raise CommandError(f'Cleanup failed: {str(e)}')
