import os
import json
import hashlib
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from audits.models import DataBackup


class Command(BaseCommand):
    help = 'Create a full database backup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            help='Name for the backup',
        )
        parser.add_argument(
            '--description',
            type=str,
            help='Description for the backup',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups/data',
            help='Directory to save the backup file',
        )

    def handle(self, *args, **options):
        name = options['name'] or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        description = options['description'] or ''
        output_dir = options['output_dir']

        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{name}.json')

        self.stdout.write(self.style.NOTICE(f'Creating backup: {name}'))

        backup = DataBackup.objects.create(
            name=name,
            description=description,
            status='IN_PROGRESS',
            file_path=output_file
        )

        try:
            with open(output_file, 'w') as f:
                call_command('dumpdata', '--indent', '2', stdout=f)

            file_size = os.path.getsize(output_file)

            sha256_hash = hashlib.sha256()
            with open(output_file, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b''):
                    sha256_hash.update(byte_block)
            checksum = sha256_hash.hexdigest()

            backup.status = 'COMPLETED'
            backup.file_size = file_size
            backup.completed_at = timezone.now()
            backup.checksum = checksum
            backup.tables_backed_up = self._get_model_list()
            backup.save()

            self.stdout.write(self.style.SUCCESS(f'Backup created successfully: {output_file}'))
            self.stdout.write(f'File size: {file_size} bytes')
            self.stdout.write(f'Checksum: {checksum}')

        except Exception as e:
            backup.status = 'FAILED'
            backup.error_message = str(e)
            backup.save()
            self.stdout.write(self.style.ERROR(f'Backup failed: {str(e)}'))

    def _get_model_list(self):
        from django.apps import apps
        models = []
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                models.append(f"{app_config.label}.{model.__name__}")
        return models
