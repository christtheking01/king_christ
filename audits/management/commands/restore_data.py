import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from audits.models import DataBackup


class Command(BaseCommand):
    help = 'Restore database from a backup file'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_id',
            type=str,
            help='ID of the backup to restore',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force restore without confirmation',
        )

    def handle(self, *args, **options):
        backup_id = options['backup_id']
        force = options['force']

        try:
            backup = DataBackup.objects.get(id=backup_id)
        except DataBackup.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Backup with ID {backup_id} not found'))
            return

        if backup.status != 'COMPLETED':
            self.stdout.write(self.style.ERROR(f'Backup status is {backup.status}, cannot restore'))
            return

        if not os.path.exists(backup.file_path):
            self.stdout.write(self.style.ERROR(f'Backup file not found: {backup.file_path}'))
            return

        if not force:
            self.stdout.write(self.style.WARNING('WARNING: This will replace all current data with the backup data!'))
            confirm = input('Are you sure you want to continue? [yes/no]: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.NOTICE('Restore cancelled'))
                return

        self.stdout.write(self.style.NOTICE(f'Restoring backup: {backup.name}'))

        try:
            call_command('loaddata', backup.file_path)
            self.stdout.write(self.style.SUCCESS('Database restored successfully'))

            AuditLog.objects.create(
                action='RESTORE',
                model_name='audit.DataBackup',
                object_id=str(backup.id),
                object_repr=backup.name,
                status='SUCCESS'
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Restore failed: {str(e)}'))

            AuditLog.objects.create(
                action='RESTORE',
                model_name='audit.DataBackup',
                object_id=str(backup.id),
                object_repr=backup.name,
                status='FAILED',
                error_message=str(e)
            )
