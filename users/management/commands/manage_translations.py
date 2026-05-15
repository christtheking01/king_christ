"""
Management command for translation utilities.
Usage:
    python manage.py manage_translations compile    - Compile all translations
    python manage.py manage_translations check      - Check translation coverage
    python manage.py manage_translations makemessages - Update .po files
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os
import subprocess


class Command(BaseCommand):
    help = 'Manage translations - compile, check, or update translation files'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['compile', 'check', 'makemessages', 'status'],
            help='Action to perform on translations'
        )
        parser.add_argument(
            '--locale',
            '-l',
            help='Specific locale to process (e.g., sw, en)'
        )

    def handle(self, *args, **options):
        action = options['action']
        locale = options.get('locale')

        if action == 'compile':
            self.compile_translations(locale)
        elif action == 'check':
            self.check_translations()
        elif action == 'makemessages':
            self.make_messages(locale)
        elif action == 'status':
            self.show_status()

    def compile_translations(self, locale=None):
        """Compile .po files to .mo files"""
        self.stdout.write(self.style.NOTICE('Compiling translations...'))

        try:
            if locale:
                call_command('compilemessages', locale=[locale], verbosity=1)
            else:
                call_command('compilemessages', verbosity=1)
            self.stdout.write(self.style.SUCCESS('Translations compiled successfully!'))
        except Exception as e:
            # Fallback to msgfmt
            self.stdout.write(self.style.WARNING(f'Django compilemessages failed: {e}'))
            self.stdout.write(self.style.NOTICE('Trying msgfmt directly...'))

            locale_dir = os.path.join(settings.BASE_DIR, 'locale')
            if locale:
                locales = [locale]
            else:
                locales = [d for d in os.listdir(locale_dir) if os.path.isdir(os.path.join(locale_dir, d))]

            for loc in locales:
                po_path = os.path.join(locale_dir, loc, 'LC_MESSAGES', 'django.po')
                mo_path = os.path.join(locale_dir, loc, 'LC_MESSAGES', 'django.mo')
                if os.path.exists(po_path):
                    try:
                        subprocess.run(['msgfmt', po_path, '-o', mo_path], check=True)
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Compiled {loc}'))
                    except Exception as e2:
                        self.stdout.write(self.style.ERROR(f'  ✗ Failed {loc}: {e2}'))

    def check_translations(self):
        """Check translation file integrity"""
        self.stdout.write(self.style.NOTICE('Checking translation files...'))

        locale_dir = os.path.join(settings.BASE_DIR, 'locale')
        for locale in os.listdir(locale_dir):
            po_path = os.path.join(locale_dir, locale, 'LC_MESSAGES', 'django.po')
            mo_path = os.path.join(locale_dir, locale, 'LC_MESSAGES', 'django.mo')

            if os.path.exists(po_path):
                po_size = os.path.getsize(po_path)
                mo_exists = os.path.exists(mo_path)
                mo_size = os.path.getsize(mo_path) if mo_exists else 0

                status = '✓' if mo_exists else '✗'
                self.stdout.write(
                    f'  {status} {locale}: django.po ({po_size} bytes)'
                    f'{" - django.mo (" + str(mo_size) + " bytes)" if mo_exists else " - django.mo MISSING"}'
                )

    def make_messages(self, locale=None):
        """Update .po files with new translatable strings"""
        self.stdout.write(self.style.NOTICE('Updating translation files...'))

        try:
            args = ['makemessages', '--all', '--ignore=venv/*', '--ignore=__pycache__/*']
            if locale:
                args.extend(['--locale', locale])
            call_command(*args, verbosity=1)
            self.stdout.write(self.style.SUCCESS('Translation files updated!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to update translations: {e}'))

    def show_status(self):
        """Show translation status"""
        self.stdout.write(self.style.NOTICE('Translation System Status'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'USE_I18N: {settings.USE_I18N}')
        self.stdout.write(f'LANGUAGE_CODE: {settings.LANGUAGE_CODE}')
        self.stdout.write(f'LANGUAGES: {settings.LANGUAGES}')
        self.stdout.write(f'LOCALE_PATHS: {settings.LOCALE_PATHS}')
        self.stdout.write(f'LANGUAGE_COOKIE_NAME: {settings.LANGUAGE_COOKIE_NAME}')
