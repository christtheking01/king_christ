from django.apps import AppConfig


class TitheConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tithe'

    def ready(self):
        import tithe.signals
        