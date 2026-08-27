from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync_roles(sender, **kwargs):
    """
    Provisionne/synchronise automatiquement les Group de rôles après
    chaque `migrate`, comme le fait Django nativement pour les
    permissions par défaut (add/change/delete/view). Évite d'oublier de
    lancer `setup_roles` manuellement après un déploiement.
    """
    from django.core.management import call_command
    call_command('setup_roles', verbosity=0)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Gestion des interventions'

    def ready(self):
        post_migrate.connect(_sync_roles, sender=self)
