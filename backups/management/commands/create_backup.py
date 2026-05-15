"""
Create database backup - Command: python manage.py create_backup
"""

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from backups.backup_manager import BackupManager


class Command(BaseCommand):
    help = 'Create a database backup and upload to cloud storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--local-only',
            action='store_true',
            help='Keep backup local, do not upload to cloud',
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            default=True,
            help='Compress backup using gzip',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Custom filename for the backup',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Creating database backup...'))
        
        try:
            manager = BackupManager()
            
            # Create backup
            backup_path = manager.create_local_backup(options.get('output'))
            self.stdout.write(f'Backup created: {backup_path}')
            
            # Compress if requested
            if options['compress']:
                backup_path = manager.compress_backup(backup_path)
                self.stdout.write(f'Backup compressed: {backup_path}')
            
            # Upload to S3 if not local-only
            if not options['local_only']:
                if not os.getenv('AWS_ACCESS_KEY_ID'):
                    self.stdout.write(
                        self.style.WARNING(
                            'AWS credentials not configured. Backup kept local only.'
                        )
                    )
                else:
                    s3_url = manager.upload_to_s3(backup_path)
                    self.stdout.write(
                        self.style.SUCCESS(f'Backup uploaded to: {s3_url}')
                    )
                    # Clean up local file after upload
                    os.remove(backup_path)
                    self.stdout.write('Local backup file removed')
            
            self.stdout.write(self.style.SUCCESS('Backup completed successfully!'))
            
        except Exception as e:
            raise CommandError(f'Backup failed: {str(e)}')
