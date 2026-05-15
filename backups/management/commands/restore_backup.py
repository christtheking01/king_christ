"""
Restore database from backup - Command: python manage.py restore_backup <backup_file>
"""

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from backups.backup_manager import BackupManager


class Command(BaseCommand):
    help = 'Restore database from a backup file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'backup_source',
            type=str,
            help='Backup file path (local) or S3 key',
        )
        parser.add_argument(
            '--from-s3',
            action='store_true',
            help='Download backup from S3 before restoring',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            required=True,
            help='Confirm restoration (WARNING: will delete current data)',
        )
        parser.add_argument(
            '--keep-backup',
            action='store_true',
            help='Keep downloaded backup file after restore',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            raise CommandError(
                'WARNING: This will DELETE ALL CURRENT DATA in the database. '
                'Use --confirm flag to proceed with restoration.'
            )
        
        backup_source = options['backup_source']
        manager = BackupManager()
        
        try:
            # Download from S3 if needed
            if options['from_s3']:
                self.stdout.write(f'Downloading backup from S3: {backup_source}')
                backup_path = manager.download_from_s3(backup_source)
                self.stdout.write(f'Backup downloaded to: {backup_path}')
            else:
                backup_path = backup_source
                if not os.path.exists(backup_path):
                    raise CommandError(f'Backup file not found: {backup_path}')
            
            # Verify backup file
            self.stdout.write(self.style.NOTICE('Verifying backup file...'))
            if not os.path.exists(backup_path):
                raise CommandError(f'Backup file not accessible: {backup_path}')
            
            # Confirm again with user
            self.stdout.write(
                self.style.WARNING(
                    '\\n' + '='*60 + '\\n'
                    'WARNING: DATABASE RESTORE OPERATION' + '\\n'
                    '='*60 + '\\n'
                    f'This will REPLACE ALL CURRENT DATA with backup: {backup_source}' + '\\n'
                    'All current data will be PERMANENTLY LOST.' + '\\n'
                    '='*60 + '\\n'
                )
            )
            
            confirm_input = input('Type "RESTORE" to confirm: ')
            if confirm_input != 'RESTORE':
                self.stdout.write(self.style.ERROR('Restore cancelled.'))
                return
            
            # Perform restore
            self.stdout.write(self.style.NOTICE('Starting restoration...'))
            manager.restore_from_backup(backup_path, confirm=True)
            
            # Cleanup
            if options['from_s3'] and not options['keep_backup']:
                os.remove(backup_path)
                self.stdout.write('Temporary backup file removed')
            
            self.stdout.write(
                self.style.SUCCESS('\\nDatabase restored successfully!')
            )
            self.stdout.write(
                'Please restart the application and verify data integrity.'
            )
            
        except Exception as e:
            raise CommandError(f'Restore failed: {str(e)}')
