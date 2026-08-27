# Ajoute les permissions personnalisées utilisées par le système de rôles
# (core/permissions.py + commande `setup_roles`). N'affecte aucune table :
# Django se contente d'enregistrer de nouvelles lignes dans auth_permission.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_incident'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='intervention',
            options={
                'ordering': ['-date_creation'],
                'verbose_name': 'Intervention',
                'verbose_name_plural': 'Interventions',
                'permissions': [
                    ('view_all_interventions',
                     "Peut voir/gérer toutes les interventions (pas seulement les siennes)"),
                    ('export_interventions',
                     "Peut exporter les interventions en CSV"),
                    ('view_statistics',
                     "Peut consulter la page de statistiques détaillées"),
                ],
            },
        ),
        migrations.AlterModelOptions(
            name='sparepart',
            options={
                'ordering': ['nom'],
                'verbose_name': 'Pièce détachée',
                'verbose_name_plural': 'Pièces détachées',
                'permissions': [
                    ('export_stock', "Peut exporter le stock en CSV"),
                ],
            },
        ),
    ]
