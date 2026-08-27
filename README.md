# OCP Gestion des Interventions — Site de Khouribga

Application web de gestion des interventions de maintenance pour le service informatique du Groupe OCP (site de Khouribga).

## Stack technique

- **Backend** : Django 4.2 (Python)
- **Frontend** : Tailwind CSS + Alpine.js (monolithe Django, pas de SPA)
- **PDF** : xhtml2pdf
- **Base de données** : SQLite (développement)

## Installation

```bash
# 1. Extraire le projet
cd ocp_intervention

# 2. Créer l'environnement virtuel
python -m venv venv

# 3. Activer
# Windows :
venv\Scripts\activate
# macOS/Linux :
source venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Appliquer les migrations
python manage.py migrate

# 6. Charger les données de démonstration
python manage.py seed_demo

# 7. Lancer le serveur
python manage.py runserver
```

Accéder à : http://127.0.0.1:8000/

## Comptes de démonstration

| Rôle | Utilisateur | Mot de passe | Groupe Django |
|------|-------------|---------------|---------------|
| Agent bureau | `admin` | `admin123` | `Agent bureau` |
| Technicien | `tech1` | `tech123` | `Technicien` |
| Manager (supervision, lecture seule) | `manager1` | `manager123` | `Manager` |
| Client (portail externe) | `client1` | `client123` | `Client` |

## Rôles et permissions (RBAC)

Les rôles sont de vrais `Group` Django, pas un simple booléen `is_staff`.
Chaque permission accordée à un rôle est un objet `Permission` Django
standard — celles générées automatiquement pour chaque modèle
(`add_<modele>` / `change_<modele>` / `delete_<modele>` / `view_<modele>`)
plus quelques permissions personnalisées (`view_all_interventions`,
`export_interventions`, `view_statistics`, `export_stock`).

- **`core/permissions.py`** — source de vérité unique : le dict
  `ROLE_PERMISSIONS` associe chaque rôle à sa liste de permissions, plus
  les décorateurs de vue (`perm_required`, `any_perm_required`) et la
  règle d'accès objet (`user_can_access_intervention` — un technicien
  n'agit que sur SES interventions, ce qu'aucune permission "par modèle"
  ne peut exprimer).
- **`python manage.py setup_roles`** — crée/synchronise les `Group` en
  base à partir de `ROLE_PERMISSIONS`. Lancée automatiquement après
  chaque `migrate` (signal `post_migrate` dans `core/apps.py`), donc en
  temps normal vous n'avez jamais besoin de la lancer à la main.
- **`is_staff`** ne sert plus qu'à son usage Django natif : autoriser
  l'accès à `/admin/`. Ce n'est plus un indicateur de rôle métier dans
  le code applicatif (les vues utilisent `request.user.has_perm(...)`
  ou `{% if perms.core.xxx %}` dans les templates).

### Rôles fournis

- **Agent bureau** : CRUD complet (clients, techniciens, pièces,
  mouvements de stock), création/suppression/réassignation des
  interventions, statistiques, journal d'activité, exports CSV.
- **Technicien** : lecture seule sur clients/techniciens/stock, ne voit
  et ne modifie que ses propres interventions (règle appliquée au
  niveau de l'objet, pas du rôle), ajoute tâches/pièces/rapports sur ces
  dernières. Pas de suppression, pas de mouvements de stock manuels.
- **Manager** : supervision globale en lecture seule (toutes les
  interventions, statistiques, journal d'activité, exports) — sans
  aucun droit de création/modification/suppression.
- **Client** : rôle externe, réservé au portail client (`/portail/`).
  Ne voit que SES propres interventions (règle appliquée au niveau de
  l'objet via `user_can_access_intervention`, comme pour le
  technicien), en lecture seule, avec possibilité d'échanger des
  messages sur ces interventions. Aucun accès aux référentiels
  internes (clients, techniciens, stock), ni à la recherche globale,
  ni aux vues de gestion — `is_portal_client()` détecte ce type de
  compte et le redirige systématiquement vers `/portail/` s'il tente
  d'accéder à une URL interne.

### Ajouter un nouveau rôle

Ajoutez une entrée dans `ROLE_PERMISSIONS` (`core/permissions.py`) avec
la liste des `codename` de permissions souhaitées, puis relancez
`python manage.py setup_roles` (ou redéployez : `migrate` le fait pour
vous). **Aucune vue ni template n'a besoin d'être modifié** — c'était le
principal défaut de l'ancien modèle basé sur `is_staff`, qui ne pouvait
exprimer que deux rôles en dur.

### Portail client

Une fiche `Client` peut être liée à un compte Django via `Client.user`
(FK `OneToOne`, ajoutée en même temps que le rôle `Client` — même
principe que `Technician.user`). Une fois liée, le client se connecte
avec ce compte et accède à un espace dédié, distinct de l'interface
interne :

- `/portail/` — tableau de bord : ses interventions (actives puis
  terminées), tous statuts confondus.
- `/portail/interventions/<id>/` — détail en lecture seule d'une de
  SES interventions, avec fil de messages (le client peut écrire,
  mais ne voit ni les tâches internes, ni les pièces/coûts, ni les
  recommandations de technicien — vues volontairement séparées des
  vues internes, voir `core/views.py::client_portal_*`).

Un compte `Client` est automatiquement redirigé vers `/portail/` s'il
essaie d'accéder à une URL interne (`is_portal_client()` dans
`core/permissions.py`), et ne peut consulter/modifier que les
interventions dont il est le client (`user_can_access_intervention`).
Toute fiche `Client` sans compte lié (`user=None`) continue de
fonctionner comme avant : gérée uniquement par l'agent bureau, sans
accès applicatif direct.

## Fonctionnalités clés

- Planification et affectation des interventions
- **Assignation manuelle du technicien** (voir section dédiée ci-dessous)
- Suivi en temps réel (statuts, retard)
- Recommandation de technicien (moteur de scoring pondéré explicable)
- Analyse de description par mots-clés (suggestion de priorité)
- Gestion centralisée des stocks (StockService — traçabilité complète)
- Messagerie par intervention
- **Portail client dédié** (`/portail/`) — voir section RBAC ci-dessus
- Rapports avec génération PDF
- Tableau de bord opérationnel + page de statistiques détaillées
- Export CSV interventions et stock
- Journal d'activité
- Recherche globale

## Assignation du technicien

L'agent bureau (ou tout rôle disposant de `core.change_intervention`)
choisit **librement** le technicien à assigner à une intervention,
directement depuis la page de détail (`/interventions/<id>/`) — pas
besoin de repasser par le formulaire complet d'édition :

- **Assignation en un clic** sur une des recommandations du moteur de
  scoring (top 3, avec le détail du score sur 100).
- **Choix libre parmi tous les techniciens** via le menu déroulant
  « Choisir un autre technicien », que le technicien souhaité figure ou
  non dans le top 3 recommandé.
- Fonctionne aussi bien pour une **première assignation** que pour une
  **réassignation** (changer le technicien déjà en charge).

Techniquement :

- `InterventionAssignForm` (`core/forms.py`) — formulaire dédié,
  `ModelChoiceField` sur `Technician.objects.all()`.
- `intervention_assign_technician` (`core/views.py`) — vue POST-only,
  protégée par `@perm_required('core.change_intervention')`, qui
  enregistre le changement, déclenche `notifier_assignation` et journalise
  l'action (`ActivityLog` : « Assignation intervention » ou
  « Réassignation intervention »).
- Route : `interventions/<id>/assigner/` → `intervention_assign_technician`.

Le moteur de recommandation (`recommander_technicien`, section
précédente) reste un **conseil**, jamais une contrainte : il suggère,
l'agent décide.

## Architecture du stock

Le champ `quantite_stock` n'est **jamais** modifié directement par formulaire. Toute variation passe par `StockService.adjust()` qui crée un `StockMovement` et garantit la cohérence des données.
