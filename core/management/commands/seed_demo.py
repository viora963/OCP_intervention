import random

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User, Group
from django.utils import timezone
from core.models import (
    Client, Technician, SparePart, Intervention, Report, Task, Incident,
    StockMovement, Message, ActivityLog, ClientEvaluation, InterventionPiece,
)
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

        # ─────────────────────────────────────────────────────────
        # Comptes supplémentaires — pour arriver à 20 utilisateurs au
        # total (4 ci-dessus + 16 ci-dessous), répartis sur les 4 rôles
        # existants : Agent bureau, Technicien, Manager, Client.
        # ─────────────────────────────────────────────────────────

        def make_user(username, email, first_name, last_name, password, group_name):
            u, _ = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'first_name': first_name, 'last_name': last_name}
            )
            u.set_password(password)
            u.save()
            u.groups.add(Group.objects.get(name=group_name))
            return u

        # 2 Agents bureau supplémentaires (total Agent bureau : 3 avec admin)
        agent2_user = make_user('agent2', 'agent2@ocp.ma', 'Nadia', 'Chraibi', 'agent2pass123', AGENT_BUREAU)
        agent3_user = make_user('agent3', 'agent3@ocp.ma', 'Younes', 'Berrada', 'agent3pass123', AGENT_BUREAU)

        # 2 comptes Technicien pour des techniciens déjà présents en démo
        # (tech2/tech3 existaient sans compte utilisateur) + 5 nouveaux
        # techniciens (total Technicien : 8 avec tech1)
        tech2_user = make_user('tech2', 'tech2@ocp.ma', 'Said', 'Bennani', 'tech2pass123', TECHNICIEN)
        tech3_user = make_user('tech3', 'tech3@ocp.ma', 'Laila', 'Fassi', 'tech3pass123', TECHNICIEN)
        tech4_user = make_user('tech4', 'tech4@ocp.ma', 'Omar', 'Kabbaj', 'tech4pass123', TECHNICIEN)
        tech5_user = make_user('tech5', 'tech5@ocp.ma', 'Imane', 'Sefrioui', 'tech5pass123', TECHNICIEN)
        tech6_user = make_user('tech6', 'tech6@ocp.ma', 'Youssef', 'Ouazzani', 'tech6pass123', TECHNICIEN)
        tech7_user = make_user('tech7', 'tech7@ocp.ma', 'Amal', 'Benjelloun', 'tech7pass123', TECHNICIEN)
        tech8_user = make_user('tech8', 'tech8@ocp.ma', 'Hicham', 'Rifi', 'tech8pass123', TECHNICIEN)

        # 2 Managers supplémentaires (total Manager : 3 avec manager1)
        manager2_user = make_user('manager2', 'manager2@ocp.ma', 'Karima', 'Lahlou', 'manager2pass123', MANAGER)
        manager3_user = make_user('manager3', 'manager3@ocp.ma', 'Rachid', 'Amrani', 'manager3pass123', MANAGER)

        # 5 comptes Client supplémentaires (total Client : 6 avec client1)
        client2_user = make_user('client2', 'contact@silo-est.ma', 'Nawal', 'Zidane', 'client2pass123', CLIENT)
        client3_user = make_user('client3', 'contact@centrale-elec.ma', 'Mehdi', 'Toumi', 'client3pass123', CLIENT)
        client4_user = make_user('client4', 'contact@labo-qualite.ma', 'Fatima', 'Rguibi', 'client4pass123', CLIENT)
        client5_user = make_user('client5', 'contact@parc-flotte.ma', 'Anas', 'Belkadi', 'client5pass123', CLIENT)
        client6_user = make_user('client6', 'contact@zone-portuaire.ma', 'Salma', 'Ezzahiri', 'client6pass123', CLIENT)

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
            defaults={
                'email': 'silo.est@ocp.ma', 'telephone': '0523-222222', 'secteur': 'Logistique',
                'user': client2_user,
            }
        )
        c3, _ = Client.objects.get_or_create(
            nom='Centrale Électrique',
            defaults={
                'email': 'centrale.elec@ocp.ma', 'telephone': '0523-333333', 'secteur': 'Énergie',
                'user': client3_user,
            }
        )
        c4, _ = Client.objects.get_or_create(
            nom='Laboratoire Qualité',
            defaults={
                'email': 'labo.qualite@ocp.ma', 'telephone': '0523-444444', 'secteur': 'Contrôle qualité',
                'user': client4_user,
            }
        )
        c5, _ = Client.objects.get_or_create(
            nom='Parc Flotte & Engins',
            defaults={
                'email': 'parc.flotte@ocp.ma', 'telephone': '0523-555555', 'secteur': 'Logistique',
                'user': client5_user,
            }
        )
        c6, _ = Client.objects.get_or_create(
            nom='Zone Portuaire',
            defaults={
                'email': 'zone.portuaire@ocp.ma', 'telephone': '0523-666666', 'secteur': 'Export',
                'user': client6_user,
            }
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
                'user': tech2_user,
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
                'user': tech3_user,
                'nom': 'Fassi', 'prenom': 'Laila',
                'telephone': '0611-333333',
                'specialites': 'inspection, securite, urgence',
                'disponible': False,
                'localisation': 'Site Sud',
                'latitude': 32.82, 'longitude': -6.92,
                'note_moyenne': 4.5
            }
        )
        t4, _ = Technician.objects.get_or_create(
            email='tech4@ocp.ma',
            defaults={
                'user': tech4_user,
                'nom': 'Kabbaj', 'prenom': 'Omar',
                'telephone': '0611-444444',
                'specialites': 'mecanique, hydraulique',
                'disponible': True,
                'localisation': 'Atelier Central',
                'latitude': 32.87, 'longitude': -6.91,
                'note_moyenne': 4.0
            }
        )
        t5, _ = Technician.objects.get_or_create(
            email='tech5@ocp.ma',
            defaults={
                'user': tech5_user,
                'nom': 'Sefrioui', 'prenom': 'Imane',
                'telephone': '0611-555555',
                'specialites': 'electricite, automatisme',
                'disponible': True,
                'localisation': 'Zone Nord',
                'latitude': 32.90, 'longitude': -6.87,
                'note_moyenne': 4.3
            }
        )
        t6, _ = Technician.objects.get_or_create(
            email='tech6@ocp.ma',
            defaults={
                'user': tech6_user,
                'nom': 'Ouazzani', 'prenom': 'Youssef',
                'telephone': '0611-666666',
                'specialites': 'reseau, informatique',
                'disponible': False,
                'localisation': 'Centre de contrôle',
                'latitude': 32.86, 'longitude': -6.89,
                'note_moyenne': 3.9
            }
        )
        t7, _ = Technician.objects.get_or_create(
            email='tech7@ocp.ma',
            defaults={
                'user': tech7_user,
                'nom': 'Benjelloun', 'prenom': 'Amal',
                'telephone': '0611-777777',
                'specialites': 'maintenance, inspection',
                'disponible': True,
                'localisation': 'Site Sud',
                'latitude': 32.81, 'longitude': -6.93,
                'note_moyenne': 4.1
            }
        )
        t8, _ = Technician.objects.get_or_create(
            email='tech8@ocp.ma',
            defaults={
                'user': tech8_user,
                'nom': 'Rifi', 'prenom': 'Hicham',
                'telephone': '0611-888888',
                'specialites': 'urgence, reparation',
                'disponible': True,
                'localisation': 'Zone Industrielle',
                'latitude': 32.84, 'longitude': -6.86,
                'note_moyenne': 3.7
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
        p6, _ = SparePart.objects.get_or_create(
            reference='ROU-BLR-006',
            defaults={'nom': 'Roulement à billes', 'description': 'Roulement pour convoyeur', 'quantite_stock': 30, 'quantite_minimale': 8, 'prix_unitaire': 180.00, 'fournisseur': 'SKF Maroc', 'emplacement': 'Entrepôt A-05'}
        )
        p7, _ = SparePart.objects.get_or_create(
            reference='COU-TRP-007',
            defaults={'nom': 'Courroie trapézoïdale', 'description': 'Courroie de transmission', 'quantite_stock': 18, 'quantite_minimale': 5, 'prix_unitaire': 220.00, 'fournisseur': 'Gates', 'emplacement': 'Entrepôt A-06'}
        )
        p8, _ = SparePart.objects.get_or_create(
            reference='VAN-HYD-008',
            defaults={'nom': 'Vanne hydraulique', 'description': 'Vanne de régulation de débit', 'quantite_stock': 5, 'quantite_minimale': 2, 'prix_unitaire': 3200.00, 'fournisseur': 'Bosch Rexroth', 'emplacement': 'Entrepôt A-02'}
        )
        p9, _ = SparePart.objects.get_or_create(
            reference='DIS-DUR-009',
            defaults={'nom': 'Disjoncteur 63A', 'description': 'Protection électrique triphasée', 'quantite_stock': 22, 'quantite_minimale': 6, 'prix_unitaire': 450.00, 'fournisseur': 'Schneider', 'emplacement': 'Entrepôt B-01'}
        )
        p10, _ = SparePart.objects.get_or_create(
            reference='JOI-ETA-010',
            defaults={'nom': "Joint d'étanchéité", 'description': 'Joint torique haute pression', 'quantite_stock': 60, 'quantite_minimale': 15, 'prix_unitaire': 15.00, 'fournisseur': 'Parker', 'emplacement': 'Entrepôt B-09'}
        )
        p11, _ = SparePart.objects.get_or_create(
            reference='VAR-FRQ-011',
            defaults={'nom': 'Variateur de fréquence', 'description': 'Variateur de vitesse moteur', 'quantite_stock': 4, 'quantite_minimale': 2, 'prix_unitaire': 8500.00, 'fournisseur': 'ABB', 'emplacement': 'Entrepôt A-03'}
        )
        p12, _ = SparePart.objects.get_or_create(
            reference='LUB-HUI-012',
            defaults={'nom': 'Huile lubrifiante 20L', 'description': 'Lubrifiant industriel multigrade', 'quantite_stock': 40, 'quantite_minimale': 10, 'prix_unitaire': 320.00, 'fournisseur': 'Total Maroc', 'emplacement': 'Entrepôt C-01'}
        )
        p13, _ = SparePart.objects.get_or_create(
            reference='DET-GAZ-013',
            defaults={'nom': 'Détecteur de gaz', 'description': 'Capteur de sécurité gaz toxique', 'quantite_stock': 9, 'quantite_minimale': 4, 'prix_unitaire': 1900.00, 'fournisseur': 'Honeywell', 'emplacement': 'Entrepôt C-08'}
        )
        p14, _ = SparePart.objects.get_or_create(
            reference='FIL-AIR-014',
            defaults={'nom': 'Filtre à air industriel', 'description': 'Filtre haute capacité', 'quantite_stock': 25, 'quantite_minimale': 8, 'prix_unitaire': 95.00, 'fournisseur': 'Mann Filter', 'emplacement': 'Entrepôt B-04'}
        )
        p15, _ = SparePart.objects.get_or_create(
            reference='BAT-12V-015',
            defaults={'nom': 'Batterie 12V industrielle', 'description': 'Batterie de secours onduleur', 'quantite_stock': 14, 'quantite_minimale': 5, 'prix_unitaire': 680.00, 'fournisseur': 'Exide', 'emplacement': 'Entrepôt C-11'}
        )

        toutes_pieces = [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15]

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

        # Tâches (5 interventions de base)
        Task.objects.get_or_create(intervention=i2, titre='Poser supports muraux', defaults={'statut': 'terminee'})
        Task.objects.get_or_create(intervention=i2, titre='Brancher câbles POE', defaults={'statut': 'en_cours'})
        Task.objects.get_or_create(intervention=i2, titre='Configurer enregistreur NVR', defaults={'statut': 'a_faire'})

        # Incidents (5 interventions de base)
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

        # Rapport (intervention #1)
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

        # ─────────────────────────────────────────────────────────
        # Volume supplémentaire — 25 interventions de plus (ids 6 à 30,
        # total 30), avec tâches, incidents, rapports, évaluations,
        # messages et mouvements de stock associés, pour avoir un jeu de
        # données plus représentatif sur chaque entité.
        # ─────────────────────────────────────────────────────────
        rng = random.Random(42)  # seed fixe : ré-exécuter la commande produit le même volume

        tous_clients = [c1, c2, c3, c4, c5, c6]
        tous_techniciens = [t1, t2, t3, t4, t5, t6, t7, t8]
        tous_agents = [admin_user, agent2_user, agent3_user]
        tous_managers = [manager_user, manager2_user, manager3_user]

        titres_par_type = {
            'maintenance': ['Maintenance préventive convoyeur', 'Révision groupe motopompe', 'Entretien tableau électrique', 'Contrôle périodique compresseur'],
            'reparation': ['Réparation fuite hydraulique', 'Remplacement roulement défectueux', 'Réparation courroie rompue', 'Dépannage armoire électrique'],
            'installation': ['Installation nouvelle vanne', 'Installation variateur de fréquence', 'Mise en place détecteur de gaz', 'Installation éclairage LED atelier'],
            'urgence': ["Arrêt d'urgence ligne production", 'Fuite de gaz signalée', 'Panne totale alimentation électrique', 'Surchauffe moteur principal'],
            'inspection': ['Inspection annuelle sécurité', 'Contrôle réglementaire levage', 'Inspection réseau électrique', 'Audit conformité incendie'],
        }
        localisations = ['Atelier Broyage Nord', 'Silo Est', 'Centrale Électrique', 'Laboratoire Qualité', 'Parc Flotte', 'Zone Portuaire', 'Zone Industrielle', 'Site Sud']
        statuts_pool = ['terminee'] * 5 + ['en_cours'] * 2 + ['planifiee'] * 2 + ['en_attente'] * 3 + ['annulee'] * 1
        priorites_pool = ['basse', 'moyenne', 'moyenne', 'haute', 'critique']

        interventions_generees = []
        for idx in range(6, 31):
            # Toutes les valeurs aléatoires de cette itération sont tirées
            # ICI, inconditionnellement — jamais à l'intérieur d'un `if`
            # qui dépend de l'état déjà présent en base (ex. `created`).
            # Sinon le nombre de tirages varie selon que l'objet existe
            # déjà, ce qui décale la séquence aléatoire à chaque
            # ré-exécution et casse l'idempotence de la commande.
            type_intervention = rng.choice(list(titres_par_type.keys()))
            titre = rng.choice(titres_par_type[type_intervention])
            statut = rng.choice(statuts_pool)
            client = rng.choice(tous_clients)
            sans_technicien = rng.random() < 0.15  # ~15% restent non assignées, comme i5
            technicien = rng.choice(tous_techniciens)  # tiré même si pas utilisé, pour garder la séquence stable
            if sans_technicien:
                technicien = None
            duree_estimee = rng.choice([30, 45, 60, 90, 120, 180, 240])
            jours_decalage = rng.randint(-15, 15)
            heure_decalage = rng.randint(0, 23)
            priorite = rng.choice(priorites_pool)
            createur = rng.choice(tous_agents)
            localisation = rng.choice(localisations)
            jitter_fin = rng.randint(-15, 30)
            veut_pieces = rng.random() < 0.4
            n_pieces = rng.randint(1, 2)
            pieces_tirees = rng.sample(toutes_pieces, k=n_pieces)
            qtes_pieces = [rng.randint(1, 2) for _ in pieces_tirees]
            n_taches = rng.randint(1, 3)
            statuts_taches = [rng.choice(['a_faire', 'en_cours', 'terminee']) for _ in range(n_taches)]
            veut_incident = rng.random() < 0.2
            gravite_incident = rng.choice(['mineure', 'moderee', 'majeure', 'critique'])
            technicien_incident = rng.choice(tous_techniciens)
            incident_resolu = rng.random() < 0.6
            satisfaction = rng.randint(3, 5)
            note_intervention = rng.randint(3, 5)
            note_technicien = rng.randint(60, 100)
            n_messages = rng.randint(0, 2)

            date_planif = timezone.now() + timezone.timedelta(days=jours_decalage, hours=heure_decalage)

            inter, created = Intervention.objects.get_or_create(
                id=idx,
                defaults={
                    'titre': f"{titre} #{idx}",
                    'description': f"{titre} sur site {client.nom}.",
                    'client': client, 'technicien': technicien,
                    'type_intervention': type_intervention,
                    'priorite': priorite,
                    'statut': statut,
                    'date_planification': date_planif,
                    'duree_estimee': duree_estimee,
                    'localisation': localisation,
                    'created_by': createur,
                }
            )
            if created and statut in ('en_cours', 'terminee'):
                inter.date_debut = date_planif
                if statut == 'terminee':
                    inter.date_fin = inter.date_debut + timezone.timedelta(minutes=duree_estimee + jitter_fin)
                inter.save()
            interventions_generees.append(inter)

            # Pièces utilisées sur ~40% des interventions (lien InterventionPiece
            # + mouvement de stock tracé via StockService, sans jamais faire
            # baisser le stock sous zéro)
            if veut_pieces:
                acteur = technicien.user if (technicien and technicien.user) else admin_user
                for piece, qte in zip(pieces_tirees, qtes_pieces):
                    _, piece_created = InterventionPiece.objects.get_or_create(
                        intervention=inter, piece=piece, defaults={'quantite': qte}
                    )
                    if piece_created:
                        try:
                            StockService.consommer_pour_intervention(inter, piece, qte, acteur)
                        except ValueError:
                            pass  # stock insuffisant en démo : le lien reste, sans mouvement

            # 1 à 3 tâches par intervention
            for t_idx, statut_tache in enumerate(statuts_taches):
                Task.objects.get_or_create(
                    intervention=inter,
                    titre=f"Étape {t_idx + 1} — {titre.lower()}",
                    defaults={'statut': statut_tache}
                )

            # Incident sur ~20% des interventions
            if veut_incident:
                Incident.objects.get_or_create(
                    intervention=inter,
                    titre=f"Anomalie détectée — {titre.lower()}",
                    defaults={
                        'description': "Problème constaté sur le terrain nécessitant un suivi.",
                        'gravite': gravite_incident,
                        'signale_par': technicien_incident.user or admin_user,
                        'resolu': incident_resolu,
                    }
                )

            # Rapport + évaluation client pour les interventions terminées
            if statut == 'terminee':
                rep, _ = Report.objects.get_or_create(
                    intervention=inter,
                    defaults={
                        'contenu': f"Intervention réalisée avec succès sur {client.nom}.",
                        'observations': "RAS, fonctionnement nominal après intervention.",
                        'recommandations': "Prochain contrôle recommandé dans 6 mois.",
                        'satisfaction_client': satisfaction,
                    }
                )
                rep.generer_complet()

                ClientEvaluation.objects.get_or_create(
                    intervention=inter,
                    defaults={
                        'note_intervention': note_intervention,
                        'note_technicien': note_technicien,
                        'commentaire': "Intervention rapide et bien menée.",
                    }
                )

            # 0 à 2 messages échangés sur l'intervention. `contenu` porte
            # le numéro du message : c'est la clé d'unicité fonctionnelle
            # ici (get_or_create ne matche que sur intervention+contenu),
            # donc le nombre de messages doit venir d'une valeur déjà
            # tirée ci-dessus (n_messages), jamais d'un nouveau tirage.
            expediteurs_possibles = [admin_user] + ([technicien.user] if technicien and technicien.user else []) + \
                ([client.user] if client.user else [])
            expediteurs_tires = [rng.choice(expediteurs_possibles) for _ in range(n_messages)]
            for m_idx, expediteur in enumerate(expediteurs_tires):
                Message.objects.get_or_create(
                    intervention=inter,
                    contenu=f"Message de suivi #{m_idx + 1} concernant cette intervention.",
                    defaults={'expediteur': expediteur},
                )

        # Mouvements de stock — 2 par pièce (une entrée, une sortie). La
        # quantité est déterministe (dérivée du pk de la pièce) et vit
        # dans `defaults`, jamais dans les champs de lookup de
        # get_or_create : une quantité aléatoire utilisée comme clé de
        # recherche créerait un nouveau mouvement à chaque ré-exécution.
        for piece in toutes_pieces:
            StockMovement.objects.get_or_create(
                piece=piece, type_mouvement='entree', raison='Réapprovisionnement fournisseur',
                defaults={'quantite': 10 + (piece.pk % 10), 'utilisateur': admin_user},
            )
            StockMovement.objects.get_or_create(
                piece=piece, type_mouvement='sortie', raison='Consommation intervention',
                defaults={'quantite': 1 + (piece.pk % 5), 'utilisateur': tous_agents[piece.pk % len(tous_agents)]},
            )

        # Journal d'activité — quelques entrées représentatives
        for auteur, action in [
            (admin_user, "Connexion au système"),
            (manager_user, "Consultation des statistiques"),
            (tech_user, "Mise à jour du statut d'une intervention"),
            (agent2_user, "Création d'une nouvelle intervention"),
            (client_user, "Consultation du portail client"),
        ]:
            ActivityLog.objects.get_or_create(utilisateur=auteur, action=action, defaults={'detail': ''})

        total_users = User.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Données de démo créées avec succès ! ({total_users} utilisateurs au total)"))
        self.stdout.write("")
        self.stdout.write(f"Agent bureau (3) — groupe « {AGENT_BUREAU} » :")
        self.stdout.write("  admin   / admin123")
        self.stdout.write("  agent2  / agent2pass123")
        self.stdout.write("  agent3  / agent3pass123")
        self.stdout.write("")
        self.stdout.write(f"Technicien (8) — groupe « {TECHNICIEN} » :")
        self.stdout.write("  tech1 / tech123")
        for n in range(2, 9):
            self.stdout.write(f"  tech{n} / tech{n}pass123")
        self.stdout.write("")
        self.stdout.write(f"Manager (3) — groupe « {MANAGER} », lecture seule :")
        self.stdout.write("  manager1 / manager123")
        self.stdout.write("  manager2 / manager2pass123")
        self.stdout.write("  manager3 / manager3pass123")
        self.stdout.write("")
        self.stdout.write(f"Client (6) — groupe « {CLIENT} », portail externe (voir /portail/) :")
        self.stdout.write("  client1 / client123")
        for n in range(2, 7):
            self.stdout.write(f"  client{n} / client{n}pass123")