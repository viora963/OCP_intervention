# Ajoute Client.user : lie (optionnellement) une fiche Client à un compte
# Django, exactement comme Technician.user le fait déjà pour les
# techniciens. C'est ce qui active le portail client (lecture seule sur
# SES interventions + messagerie) — voir core/permissions.py (rôle
# "Client") et core/views.py (vues client_portal_*).

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0003_role_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='user',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='client_profile',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Compte utilisateur (portail client)',
            ),
        ),
    ]
