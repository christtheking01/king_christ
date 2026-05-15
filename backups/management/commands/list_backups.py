"""
List available backups - Command: python manage.py list_backups
"""

from django.core.management.base import BaseCommand, CommandError
from backups.backup_manager import BackupManager
from datetime import datetime


class Command(BaseCommand):
    help = 'List available database backups'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--local',
            action='store_true',
            help='List local backups only',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Number of backups to show (default: 20)',
        )

    def format_size(self, size_bytes):
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def handle(self, *args, **options):
        manager = BackupManager()
        
        if options['local']:
            # List local backups
            backup_dir = manager.backup_dir
            if not backup_dir.exists():
                self.stdout.write('No local backup directory found.')
                return
            
            backups = sorted(
                backup_dir.glob('db_backup_*.sql*'),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:options['limit']]
            
            if not backups:
                self.stdout.write('No local backups found.')
                return
            
            self.stdout.write(self.style.NOTICE(f'\\nLocal Backups (showing {len(backups)}):'))
            self.stdout.write('='*80)
            
            for i, backup in enumerate(backups, 1):
                stat = backup.stat()
                size = self.format_size(stat.st_size)
                date = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                self.stdout.write(f"{i}. {backup.name}")
                self.stdout.write(f"   Size: {size} | Created: {date}")
                self.stdout.write('')
        
        else:
            # List S3 backups
            try:
                backups = manager.list_s3_backups()
                if not backups:
                    self.stdout.write('No backups found in cloud storage.')
                    return
                
                self.stdout.write(
                    self.style.NOTICE(f'\\nCloud Backups (showing {len(backups[:options["limit"]])}):')
                )
                self.stdout.write('='*80)
                
                for i, backup in enumerate(backups[:options['limit']], 1):
                    size = self.format_size(backup['size'])
                    date = backup['last_modified'].strftime('%Y-%m-%d %H:%M:%S')
                    key = backup['key']
                    
                    self.stdout.write(f"{i}. {key.split('/')[-1]}")
                    self.stdout.write(f"   Size: {size} | Created: {date}")
                    self.stdout.write(f"   S3 Key: {key}")
                    self.stdout.write('')
                
                self.stdout.write('='*80)
                self.stdout.write(f'Total backups: {len(backups)}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Could not list cloud backups: {str(e)}')
                )
                self.stdout.write(
                    'Check your AWS credentials configuration.'
                )
