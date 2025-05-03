from django.apps import AppConfig

class LsdashConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'LSDash'

    def ready(self):
        import LSDash.signals
