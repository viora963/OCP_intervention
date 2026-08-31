# OCP Khouribga — Gestion des Interventions

Application web de gestion des interventions de maintenance, développée dans le cadre d'un stage au sein du service informatique du **Groupe OCP, site de Khouribga**.

L'application couvre l'ensemble du cycle de vie d'une intervention de maintenance : réception de la demande, planification, assignation intelligente d'un technicien, suivi en temps réel, gestion du stock de pièces détachées, rapport automatisé et retour du client.

---

## Sommaire

- [Contexte du stage](#contexte-du-stage)
- [Fonctionnalités](#fonctionnalités)
- [Stack technique](#stack-technique)
- [Rôles et permissions](#rôles-et-permissions)
- [Modèle de données](#modèle-de-données)
- [Décisions d'architecture](#décisions-darchitecture)
- [Installation](#installation)
- [Structure du projet](#structure-du-projet)
- [Roadmap / pistes d'évolution](#roadmap--pistes-dévolution)

---

## Contexte du stage

Le sujet de stage demandait la mise en place d'un système permettant :

- la gestion complète des interventions de maintenance (planification, assignation, suivi) ;
- la gestion du stock de pièces détachées ;
- un suivi en temps réel de l'état d'avancement des interventions, de la disponibilité des techniciens et des incidents rencontrés sur le terrain ;
- la génération de rapports détaillés ;
- une communication fluide entre les équipes internes et les clients.

Ce dépôt est le résultat de ce travail, développé de façon itérative sur un projet Django unique (app `core`).

---

## Fonctionnalités

### Gestion opérationnelle
- **Interventions** : création, édition, cycle de statuts (`en_attente` → `planifiee` → `en_cours` → `terminee`/`annulee`), démarrage/fin en un clic pour le technicien assigné.
- **Clients & techniciens** : fiches, référentiels, historique des interventions.
- **Stock de pièces détachées** : consommation liée à une intervention, mouvements d'entrée/sortie tracés, alertes de seuil bas.
- **Tâches** : sous-tâches par intervention, avec cycle de statut en un clic.
- **Incidents terrain** : signalement, gravité, résolution — répond explicitement au volet « incidents rencontrés » du sujet de stage.
- **Rapports** : génération semi-automatique (résumé et détection d'anomalies par règles métier, sans machine learning), export PDF.

### Assignation intelligente
- Moteur de **scoring des techniciens** (`recommander_technicien`) combinant disponibilité, spécialités, charge de travail actuelle et proximité géographique.
- Scoring affiché en direct (AJAX) **dès la création** de l'intervention, avant même son enregistrement en base — panneau latéral avec assignation en un clic.
- Recommandations également disponibles sur la fiche de détail pour réassignation.

### Suivi en temps réel
- Page dédiée (`/suivi/`) avec compteurs live, liste des interventions actives, techniciens et incidents non résolus — rafraîchie par polling (pas de WebSockets).
- Résumé compact du suivi intégré au tableau de bord principal.

### Tableau de bord
- Vue opérationnelle globale (agents bureau/managers) : KPI, jauge de taux de complétion, répartition des statuts, alertes stock, incidents non résolus, dernières interventions.
- Vue personnelle pour les techniciens de terrain (leurs interventions actives, prochaine intervention planifiée).

### Portail client
- Espace dédié, strictement cantonné aux données du client concerné : ses interventions, leur avancement, le rapport une fois disponible.
- **Messagerie** intégrée à chaque intervention entre le client et l'équipe.
- **Évaluation client** une fois l'intervention terminée : note de l'intervention (/5) et note du technicien (/100), avec commentaire libre. La note technicien alimente automatiquement la moyenne utilisée par le moteur de scoring — la satisfaction client boucle ainsi dans les futures assignations.

### Sécurité et contrôle d'accès
- RBAC basé sur les `Group`/`Permission` natifs de Django (voir [Rôles et permissions](#rôles-et-permissions)), synchronisé par une commande de gestion (`setup_roles`) exécutée automatiquement après chaque migration.
- Règles *object-level* complémentaires (un technicien n'accède qu'à ses propres interventions, un client qu'aux siennes) — non exprimables par un système de permissions par modèle seul.
- Recherche globale et listes internes explicitement fermées aux comptes du portail client.

---

## Stack technique

| Domaine | Choix |
|---|---|
| Backend | Django (Python) |
| Base de données | ORM Django (SQLite en développement) |
| Frontend | Templates Django + Tailwind CSS (CDN) + Alpine.js |
| Graphiques | Chart.js |
| Génération PDF | xhtml2pdf |
| Icônes | Phosphor Icons |
| Authentification | Système Django natif (`django.contrib.auth`) |

Aucun framework JS de build n'est utilisé — Tailwind et Alpine sont chargés en CDN, ce qui garde le projet simple à déployer pour un contexte de stage.

---

## Rôles et permissions

| Rôle | Portée |
|---|---|
| **Agent bureau** | Gestion complète : clients, techniciens, interventions, stock, rapports, statistiques, journal d'activité. Point d'entrée principal pour la création d'interventions. |
| **Technicien** | Lecture des référentiels partagés ; création/modification de rapports, tâches, incidents et messages, restreint à ses propres interventions assignées. |
| **Manager** | Lecture seule sur l'ensemble du périmètre (supervision) — aucune permission d'écriture. |
| **Client (portail)** | Accès strictement limité à ses propres interventions, à la messagerie associée et à l'évaluation post-intervention. Aucune visibilité sur les référentiels internes. |

Les rôles sont définis de façon déclarative dans `core/permissions.py::ROLE_PERMISSIONS` et provisionnés via `python manage.py setup_roles`. Ajouter un rôle ne nécessite de modifier aucune vue existante.

---

## Modèle de données

Modèles principaux (`core/models.py`) :

- **Client** — fiche client, avec lien optionnel vers un compte utilisateur (active le portail).
- **Technician** — fiche technicien, avec lien optionnel vers un compte utilisateur, localisation, note moyenne (alimentée par les évaluations clients).
- **Intervention** — cœur du système : type, priorité, statut, dates, localisation, technicien assigné.
- **InterventionPiece** — pièces consommées sur une intervention (table de liaison).
- **Task** — sous-tâches d'une intervention.
- **SparePart** / **StockMovement** — référentiel de pièces détachées et historique des mouvements de stock (toute modification de quantité passe par `StockService`, jamais en écriture directe).
- **Report** — rapport d'intervention (contenu, observations, recommandations, résumé et anomalies générés par règles métier).
- **Incident** — incident terrain rattaché à une intervention, avec gravité et statut de résolution.
- **Message** — messagerie liée à une intervention (interne et client).
- **ClientEvaluation** — évaluation du client une fois l'intervention terminée (note intervention /5, note technicien /100, commentaire).
- **ActivityLog** — journal d'activité (traçabilité des actions utilisateurs).

---

## Décisions d'architecture

Quelques choix documentés directement dans le code, résumés ici :

- **`StockService` comme source unique de vérité** : `SparePart.quantite_stock` n'est jamais modifiable par un formulaire direct — tout passe par `StockService.adjust()`, avec un `StockMovement` créé à chaque changement pour garder un historique auditable.
- **Pas de machine learning** : le scoring des techniciens et l'analyse de description reposent sur des règles métier explicites et pondérées (`utils.py`), pas sur un modèle entraîné — choix assumé et documenté dans le code (les champs nommés `ai_*` sont conservés pour compatibilité mais jamais présentés comme de l'IA à l'utilisateur).
- **Suivi temps réel par polling, pas WebSockets** : simplicité de déploiement privilégiée pour un projet de stage ; rafraîchissement toutes les 8 secondes sur la page dédiée.
- **Séparation `Report` / `ClientEvaluation`** : le rapport est un document interne rédigé par l'équipe, l'évaluation est un retour du client — deux modèles distincts pour ne jamais exposer un champ interne à une écriture cliente.
- **Portail client isolé** : vues et permissions dédiées (`client_portal_*`), plutôt que des branches conditionnelles dans les vues internes — évite qu'un champ ajouté côté interne ne se retrouve exposé au client par erreur.
- **Vérifications d'accès *object-level*** : centralisées dans `core/permissions.py` (`user_can_access_intervention`, `user_can_edit_intervention`, `user_can_message_intervention`) plutôt que dupliquées dans chaque vue.

---

## Installation

```bash
# Cloner le dépôt et se placer dedans
git clone <url-du-depot>
cd <nom-du-projet>

# Environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate

# Dépendances
pip install django xhtml2pdf

# Base de données
python manage.py migrate

# Rôles (Groups/Permissions) — normalement automatique après migrate,
# à relancer manuellement si besoin :
python manage.py setup_roles

# Compte administrateur
python manage.py createsuperuser

# Lancement
python manage.py runserver
```

L'accès au portail client ou au tableau de bord technicien nécessite de lier un compte `User` existant à une fiche `Client` ou `Technician` via `/admin/` ou les formulaires dédiés (champ « Compte utilisateur »).

---

## Structure du projet

```
core/
├── models.py                    # Modèles de données
├── views.py                     # Logique métier / vues
├── forms.py                     # Formulaires Django
├── urls.py                      # Routes
├── permissions.py               # RBAC + règles object-level
├── services.py                  # StockService (gestion du stock)
├── utils.py                     # Scoring technicien, analyse de description, notifications
│                                 #   (moteurs de règles explicites, sans machine learning —
│                                 #   voir "Décisions d'architecture")
├── context_processors.py        # Expose le rôle de l'utilisateur à tous les templates
├── admin.py                     # Interface d'administration Django
├── apps.py                      # Config de l'app ; synchronise les rôles après chaque migrate
├── management/commands/
│   ├── setup_roles.py           # Provisionne les Group/Permission (RBAC)
│   └── seed_demo.py             # Jeu de données de démonstration
├── migrations/                  # Migrations Django
├── static/core/
│   ├── css/                     # Thème visuel (Tailwind + surcharge custom)
│   └── js/app.js                # Composants Alpine partagés
└── templates/core/
    ├── base.html                    # Layout principal (interne)
    ├── base_public.html             # Layout public (login)
    ├── _sidebar.html                 # Navigation latérale
    ├── login.html                    # Connexion
    ├── dashboard.html                 # Tableau de bord staff (agent bureau / manager)
    ├── technician_dashboard.html       # Tableau de bord technicien
    ├── suivi_temps_reel.html            # Suivi en temps réel (polling)
    ├── statistics.html                   # Statistiques détaillées
    ├── search_results.html                # Recherche globale
    ├── activity_log.html                   # Journal d'activité
    ├── client_*.html                        # CRUD clients
    ├── technician_*.html                     # CRUD techniciens
    ├── intervention_*.html                    # CRUD + détail interventions
    ├── sparepart_*.html                        # CRUD pièces détachées
    ├── stock_movement_*.html                    # Mouvements de stock
    ├── report_*.html                             # Rapports (dont report_pdf.html pour l'export)
    └── client_portal_*.html                       # Portail client (dashboard + détail intervention)
```

> ⚠️ Le scoring technicien et l'analyse de description (voir plus bas) vivent tous les
> deux dans `utils.py`. Il n'y a pas de module `ai_utils.py` séparé, et la génération
> PDF des rapports se fait directement dans `views.py::report_pdf` via `xhtml2pdf`
> (pas de module `reports.py` dédié) — voir [Stack technique](#stack-technique).

---

## Roadmap / pistes d'évolution

- Notifications push (au-delà des notifications internes actuelles).
- Historique des évaluations clients sur la fiche technicien (au-delà de la moyenne actuelle).
- Export des statistiques en PDF/Excel.
- Tests automatisés (unitaires sur `StockService` et le moteur de scoring en priorité).

---

*Projet développé dans le cadre d'un stage — Génie Informatique , ENSA Khouribga.*