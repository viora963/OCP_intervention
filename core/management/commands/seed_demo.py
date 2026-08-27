from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User, Group
from django.utils import timezone
from core.models import Client, Technician, SparePart, Intervention, Report, Task, Incident
from core.services import StockService
from core.permissions import AGENT_BUREAU, TECHNICIEN, MANAGER, CLIENT


class Command(BaseCommand):
    help = 'Charge les données de démonstration'

    def handle(self, *args, **kwargs):
        self.stdout.write("Création des données de démo...")

        # S'assure que les groupes de rôles existent avant de les assigner
        # (normalement déjà fait automatiquement après `migrate`, voir
        # core/apps.py, mais on le garantit ici pour un `seed_demo` isolé).
        call_command('setup_roles', verbosity=0)

        # Utilisateurs
        # NOTE : is_staff ne sert plus qu'à autoriser l'accès à /admin/
        # (convention Django) — les permissions métier sont portées par
        # le Group assigné ci-dessous, pas par is_staff.
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'email': 'admin@ocp.ma'}
        )
        admin_user.set_password('admin123')
        admin_user.save()
        admin_user.groups.add(Group.objects.get(name=AGENT_BUREAU))

        tech_user, _ = User.objects.get_or_create(
            username='tech1',
            defaults={'is_staff': False, 'email': 'tech1@ocp.ma'}
        )
        tech_user.set_password('tech123')
        tech_user.save()
        tech_user.groups.add(Group.objects.get(name=TECHNICIEN))

        # Compte "Manager" — rôle de supervision en lecture seule, ajouté
        # pour démontrer qu'un 3e rôle se branche sans toucher aux vues.
        manager_user, _ = User.objects.get_or_create(
            username='manager1',
            defaults={'is_staff': False, 'email': 'manager1@ocp.ma', 'first_name': 'Sanae', 'last_name': 'Idrissi'}
        )
        manager_user.set_password('manager123')
        manager_user.save()
        manager_user.groups.add(Group.objects.get(name=MANAGER))

        # Compte "Client" — portail externe en lecture seule + messagerie
        # sur SES propres interventions (groupe Django « Client »).
        client_user, _ = User.objects.get_or_create(
            username='client1',
            defaults={'is_staff': False, 'email': 'contact@broyage-nord.ma', 'first_name': 'Yassine', 'last_name': 'Tazi'}
        )
        client_user.set_password('client123')
        client_user.save()
        client_user.groups.add(Group.objects.get(name=CLIENT))

        # Clients
        c1, _ = Client.objects.get_or_create(
            nom='Atelier Broyage Nord',
            defaults={
                'email': 'broyage.nord@ocp.ma', 'telephone': '0523-111111', 'secteur': 'Production',
                'user': client_user,
            }
        )
        c2, _ = Client.objects.get_or_create(
            nom='Silo Est — Phosphates',
            defaults={'email': 'silo.est@ocp.ma', 'telephone': '0523-222222', 'secteur': 'Logistique'}
        )

        # Techniciens
        t1, _ = Technician.objects.get_or_create(
            email='tech1@ocp.ma',
            defaults={
                'user': tech_user,
                'nom': 'Alami', 'prenom': 'Karim',
                'telephone': '0611-111111',
                'specialites': 'maintenance, reparation, reseau',
                'disponible': True,
                'localisation': 'Khouribga Centre',
                'latitude': 32.88, 'longitude': -6.90,
                'note_moyenne': 4.2
            }
        )
        t2, _ = Technician.objects.get_or_create(
            email='tech2@ocp.ma',
            defaults={
                'nom': 'Bennani', 'prenom': 'Said',
                'telephone': '0611-222222',
                'specialites': 'installation, electricite, climatisation',
                'disponible': True,
                'localisation': 'Zone Industrielle',
                'latitude': 32.85, 'longitude': -6.88,
                'note_moyenne': 3.8
            }
        )
        t3, _ = Technician.objects.get_or_create(
            email='tech3@ocp.ma',
            defaults={
                'nom': 'Fassi', 'prenom': 'Laila',
                'telephone': '0611-333333',
                'specialites': 'inspection, securite, urgence',
                'disponible': False,
                'localisation': 'Site Sud',
                'latitude': 32.82, 'longitude': -6.92,
                'note_moyenne': 4.5
            }
        )

        # Pièces détachées
        p1, _ = SparePart.objects.get_or_create(
            reference='MOT-220V-001',
            defaults={'nom': 'Moteur 220V', 'description': 'Moteur électrique triphasé', 'quantite_stock': 12, 'quantite_minimale': 3, 'prix_unitaire': 4500.00, 'fournisseur': 'Siemens Maroc', 'emplacement': 'Entrepôt A-12'}
        )
        p2, _ = SparePart.objects.get_or_create(
            reference='CAB-RJ45-002',
            defaults={'nom': 'Câble RJ45 50m', 'description': 'Câble réseau blindé', 'quantite_stock': 8, 'quantite_minimale': 5, 'prix_unitaire': 350.00, 'fournisseur': 'Schneider', 'emplacement': 'Entrepôt B-03'}
        )
        p3, _ = SparePart.objects.get_or_create(
            reference='FIL-10A-003',
            defaults={'nom': 'Fusible 10A', 'description': 'Fusible industriel', 'quantite_stock': 45, 'quantite_minimale': 10, 'prix_unitaire': 25.00, 'fournisseur': 'Legrand', 'emplacement': 'Entrepôt B-07'}
        )
        p4, _ = SparePart.objects.get_or_create(
            reference='POM-HYD-004',
            defaults={'nom': 'Pompe hydraulique', 'description': 'Pompe haute pression', 'quantite_stock': 2, 'quantite_minimale': 2, 'prix_unitaire': 12000.00, 'fournisseur': 'Bosch Rexroth', 'emplacement': 'Entrepôt A-01'}
        )
        p5, _ = SparePart.objects.get_or_create(
            reference='CAP-4K-005',
            defaults={'nom': 'Capteur 4K', 'description': 'Capteur vidéo surveillance', 'quantite_stock': 6, 'quantite_minimale': 4, 'prix_unitaire': 2800.00, 'fournisseur': 'Hikvision', 'emplacement': 'Entrepôt C-15'}
        )

        # Interventions
        i1, _ = Intervention.objects.get_or_create(
            id=1,
            defaults={
                'titre': 'Panne moteur broyeur principal',
                'description': 'Le moteur du broyeur principal ne démarre plus. Urgence production arrêtée.',
                'client': c1, 'technicien': t1,
                'type_intervention': 'urgence', 'priorite': 'critique', 'statut': 'terminee',
                'date_planification': timezone.now() - timezone.timedelta(days=2),
                'duree_estimee': 120, 'localisation': 'Atelier Broyage Nord'
            }
        )
        i1.date_debut = i1.date_planification
        i1.date_fin = i1.date_debut + timezone.timedelta(hours=2, minutes=30)
        i1.save()

        i2, _ = Intervention.objects.get_or_create(
            id=2,
            defaults={
                'titre': 'Installation caméras surveillance',
                'description': 'Installation de 4 nouvelles caméras 4K sur le silo Est.',
                'client': c2, 'technicien': t2,
                'type_intervention': 'installation', 'priorite': 'moyenne', 'statut': 'en_cours',
                'date_planification': timezone.now() - timezone.timedelta(hours=3),
                'duree_estimee': 240, 'localisation': 'Silo Est'
            }
        )
        i2.date_debut = timezone.now() - timezone.timedelta(hours=3)
        i2.save()

        i3, _ = Intervention.objects.get_or_create(
            id=3,
            defaults={
                'titre': 'Maintenance préventive climatisation',
                'description': 'Révision annuelle des unités de climatisation du centre de contrôle.',
                'client': c1, 'technicien': t2,
                'type_intervention': 'maintenance', 'priorite': 'basse', 'statut': 'planifiee',
                'date_planification': timezone.now() + timezone.timedelta(days=1),
                'duree_estimee': 90, 'localisation': 'Centre de contrôle'
            }
        )

        i4, _ = Intervention.objects.get_or_create(
            id=4,
            defaults={
                'titre': 'Inspection sécurité tapis roulant',
                'description': 'Inspection trimestrielle des tapis roulants — vérification des capteurs d\'arrêt d\'urgence.',
                'client': c2, 'technicien': t3,
                'type_intervention': 'inspection', 'priorite': 'haute', 'statut': 'en_attente',
                'date_planification': timezone.now() + timezone.timedelta(days=3),
                'duree_estimee': 60, 'localisation': 'Tapis roulant Silo Est'
            }
        )

        i5, _ = Intervention.objects.get_or_create(
            id=5,
            defaults={
                'titre': 'Remplacement câbles réseau',
                'description': 'Les câbles réseau du poste de supervision sont dégradés. Remplacement nécessaire.',
                'client': c1, 'technicien': None,
                'type_intervention': 'reparation', 'priorite': 'moyenne', 'statut': 'en_attente',
                'date_planification': timezone.now() + timezone.timedelta(days=5),
                'duree_estimee': 45, 'localisation': 'Poste supervision'
            }
        )

        # Tâches
        Task.objects.get_or_create(intervention=i2, titre='Poser supports muraux', defaults={'statut': 'terminee'})
        Task.objects.get_or_create(intervention=i2, titre='Brancher câbles POE', defaults={'statut': 'en_cours'})
        Task.objects.get_or_create(intervention=i2, titre='Configurer enregistreur NVR', defaults={'statut': 'a_faire'})

        # Incidents
        Incident.objects.get_or_create(
            intervention=i1,
            titre='Court-circuit au démarrage',
            defaults={
                'description': "Un court-circuit s'est produit lors du premier essai de démarrage du nouveau moteur.",
                'gravite': 'majeure',
                'signale_par': tech_user,
                'resolu': True,
            }
        )
        Incident.objects.get_or_create(
            intervention=i2,
            titre='Support mural fissuré',
            defaults={
                'description': 'Un des supports muraux livrés est fissuré, remplacement demandé au fournisseur.',
                'gravite': 'mineure',
                'signale_par': admin_user,
                'resolu': False,
            }
        )

        # Rapport
        r1, _ = Report.objects.get_or_create(
            intervention=i1,
            defaults={
                'contenu': 'Le moteur a été remplacé. Test de démarrage réussi. Production relancée.',
                'observations': 'Usure anormale des balais. Prévoir surveillance.',
                'recommandations': 'Programmer remplacement des balais dans 6 mois.',
                'satisfaction_client': 4
            }
        )
        r1.generer_complet()

        self.stdout.write(self.style.SUCCESS("Données de démo créées avec succès !"))
        self.stdout.write("Comptes :")
        self.stdout.write(f"  Agent bureau : admin/admin123     (groupe « {AGENT_BUREAU} »)")
        self.stdout.write(f"  Technicien   : tech1/tech123      (groupe « {TECHNICIEN} »)")
        self.stdout.write(f"  Manager      : manager1/manager123 (groupe « {MANAGER} », lecture seule)")
        self.stdout.write(f"  Client       : client1/client123   (groupe « {CLIENT} », portail externe — voir /portail/)")
