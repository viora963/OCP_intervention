from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from core.permissions import ROLE_PERMISSIONS


class Command(BaseCommand):
    help = (
        "Crée/synchronise les Group Django (rôles) et leurs Permission à partir "
        "de core.permissions.ROLE_PERMISSIONS. Idempotent : peut être relancée "
        "à tout moment (ex. après avoir ajouté une permission à un rôle)."
    )

    def handle(self, *args, **options):
        for role_name, codenames in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=role_name)

            permissions = []
            missing = []
            for codename in codenames:
                # `core_` prefix implicite : toutes nos permissions vivent
                # dans l'app `core`.
                try:
                    permissions.append(Permission.objects.get(
                        content_type__app_label='core',
                        codename=codename,
                    ))
                except Permission.DoesNotExist:
                    missing.append(codename)

            group.permissions.set(permissions)

            verb = "Créé" if created else "Synchronisé"
            self.stdout.write(self.style.SUCCESS(
                f"{verb} : groupe « {role_name} » — {len(permissions)} permission(s)."
            ))
            if missing:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠ Permissions introuvables (migration manquante ?) : {', '.join(missing)}"
                ))

        self.stdout.write(self.style.SUCCESS(
            "Rôles synchronisés. Pour ajouter un nouveau rôle : éditez "
            "ROLE_PERMISSIONS dans core/permissions.py puis relancez cette commande."
        ))
