from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audits'
    verbose_name = 'Audit & Security'

    def ready(self):
       import audits.signals
