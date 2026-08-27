# Generated manually for ocp_intervention v2

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=200, verbose_name='Nom')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='Email')),
                ('telephone', models.CharField(blank=True, max_length=50, verbose_name='Téléphone')),
                ('adresse', models.TextField(blank=True, verbose_name='Adresse')),
                ('secteur', models.CharField(blank=True, max_length=200, verbose_name='Secteur')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
            ],
            options={
                'verbose_name': 'Client',
                'verbose_name_plural': 'Clients',
                'ordering': ['nom'],
            },
        ),
        migrations.CreateModel(
            name='Intervention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=300, verbose_name='Titre')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('type_intervention', models.CharField(choices=[('maintenance', 'Maintenance'), ('reparation', 'Réparation'), ('installation', 'Installation'), ('urgence', 'Urgence'), ('inspection', 'Inspection')], default='maintenance', max_length=50, verbose_name='Type')),
                ('priorite', models.CharField(choices=[('basse', 'Basse'), ('moyenne', 'Moyenne'), ('haute', 'Haute'), ('critique', 'Critique')], default='moyenne', max_length=50, verbose_name='Priorité')),
                ('statut', models.CharField(choices=[('en_attente', 'En attente'), ('planifiee', 'Planifiée'), ('en_cours', 'En cours'), ('terminee', 'Terminée'), ('annulee', 'Annulée')], default='en_attente', max_length=50, verbose_name='Statut')),
                ('date_creation', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('date_planification', models.DateTimeField(blank=True, null=True, verbose_name='Date de planification')),
                ('date_debut', models.DateTimeField(blank=True, null=True, verbose_name='Date de début')),
                ('date_fin', models.DateTimeField(blank=True, null=True, verbose_name='Date de fin')),
                ('duree_estimee', models.IntegerField(default=60, help_text='Durée estimée en minutes', verbose_name='Durée estimée (min)')),
                ('localisation', models.CharField(blank=True, max_length=300, verbose_name='Localisation')),
                ('latitude', models.FloatField(blank=True, null=True, verbose_name='Latitude')),
                ('longitude', models.FloatField(blank=True, null=True, verbose_name='Longitude')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interventions', to='core.client', verbose_name='Client')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='interventions_creees', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
            ],
            options={
                'verbose_name': 'Intervention',
                'verbose_name_plural': 'Interventions',
                'ordering': ['-date_creation'],
            },
        ),
        migrations.CreateModel(
            name='SparePart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=200, verbose_name='Nom')),
                ('reference', models.CharField(max_length=100, unique=True, verbose_name='Référence')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('quantite_stock', models.IntegerField(default=0, verbose_name='Quantité en stock')),
                ('quantite_minimale', models.IntegerField(default=5, verbose_name='Quantité minimale')),
                ('prix_unitaire', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Prix unitaire')),
                ('fournisseur', models.CharField(blank=True, max_length=200, verbose_name='Fournisseur')),
                ('emplacement', models.CharField(blank=True, max_length=200, verbose_name='Emplacement')),
            ],
            options={
                'verbose_name': 'Pièce détachée',
                'verbose_name_plural': 'Pièces détachées',
                'ordering': ['nom'],
            },
        ),
        migrations.CreateModel(
            name='Technician',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100, verbose_name='Nom')),
                ('prenom', models.CharField(max_length=100, verbose_name='Prénom')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='Email')),
                ('telephone', models.CharField(blank=True, max_length=50, verbose_name='Téléphone')),
                ('specialites', models.TextField(blank=True, help_text='Compétences séparées par des virgules', verbose_name='Spécialités')),
                ('disponible', models.BooleanField(default=True, verbose_name='Disponible')),
                ('localisation', models.CharField(blank=True, max_length=300, verbose_name='Localisation')),
                ('latitude', models.FloatField(blank=True, null=True, verbose_name='Latitude')),
                ('longitude', models.FloatField(blank=True, null=True, verbose_name='Longitude')),
                ('note_moyenne', models.FloatField(default=0.0, verbose_name='Note moyenne')),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='technician_profile', to=settings.AUTH_USER_MODEL, verbose_name='Compte utilisateur')),
            ],
            options={
                'verbose_name': 'Technicien',
                'verbose_name_plural': 'Techniciens',
                'ordering': ['nom', 'prenom'],
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=300, verbose_name='Titre')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('statut', models.CharField(choices=[('a_faire', 'À faire'), ('en_cours', 'En cours'), ('terminee', 'Terminée')], default='a_faire', max_length=50, verbose_name='Statut')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('intervention', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='core.intervention', verbose_name='Intervention')),
            ],
            options={
                'verbose_name': 'Tâche',
                'verbose_name_plural': 'Tâches',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_mouvement', models.CharField(choices=[('entree', 'Entrée'), ('sortie', 'Sortie')], max_length=50, verbose_name='Type de mouvement')),
                ('quantite', models.PositiveIntegerField(verbose_name='Quantité')),
                ('raison', models.TextField(blank=True, verbose_name='Raison')),
                ('date_mouvement', models.DateTimeField(auto_now_add=True, verbose_name='Date du mouvement')),
                ('piece', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mouvements', to='core.sparepart', verbose_name='Pièce')),
                ('utilisateur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur')),
            ],
            options={
                'verbose_name': 'Mouvement de stock',
                'verbose_name_plural': 'Mouvements de stock',
                'ordering': ['-date_mouvement'],
            },
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contenu', models.TextField(blank=True, verbose_name='Contenu du rapport')),
                ('observations', models.TextField(blank=True, verbose_name='Observations')),
                ('recommandations', models.TextField(blank=True, verbose_name='Recommandations')),
                ('satisfaction_client', models.IntegerField(blank=True, choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], null=True, verbose_name='Satisfaction client (1-5)')),
                ('ai_summary', models.TextField(blank=True, verbose_name='Résumé automatique')),
                ('ai_anomalies', models.TextField(blank=True, verbose_name='Anomalies détectées')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('intervention', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='report', to='core.intervention', verbose_name='Intervention')),
            ],
            options={
                'verbose_name': 'Rapport',
                'verbose_name_plural': 'Rapports',
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contenu', models.TextField(verbose_name='Contenu')),
                ('date_envoi', models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")),
                ('expediteur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Expéditeur')),
                ('intervention', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='core.intervention', verbose_name='Intervention')),
            ],
            options={
                'verbose_name': 'Message',
                'verbose_name_plural': 'Messages',
                'ordering': ['date_envoi'],
            },
        ),
        migrations.CreateModel(
            name='InterventionPiece',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantite', models.PositiveIntegerField(default=1, verbose_name='Quantité')),
                ('date_utilisation', models.DateTimeField(auto_now_add=True, verbose_name="Date d'utilisation")),
                ('intervention', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.intervention', verbose_name='Intervention')),
                ('piece', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.sparepart', verbose_name='Pièce')),
            ],
            options={
                'verbose_name': 'Pièce utilisée',
                'verbose_name_plural': 'Pièces utilisées',
                'unique_together': {('intervention', 'piece')},
            },
        ),
        migrations.AddField(
            model_name='intervention',
            name='pieces_utilisees',
            field=models.ManyToManyField(blank=True, through='core.InterventionPiece', to='core.sparepart', verbose_name='Pièces utilisées'),
        ),
        migrations.AddField(
            model_name='intervention',
            name='technicien',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='intervention_set', to='core.technician', verbose_name='Technicien'),
        ),
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=200, verbose_name='Action')),
                ('detail', models.TextField(blank=True, verbose_name='Détail')),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name='Date')),
                ('utilisateur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur')),
            ],
            options={
                "verbose_name": "Journal d'activité",
                "verbose_name_plural": "Journal d'activité",
                'ordering': ['-date'],
            },
        ),
    ]
