"""
Contrôle d'accès basé sur les rôles (RBAC).

Architecture
------------
Les permissions "métier" (qui peut créer un client, supprimer une
intervention, exporter le stock, consulter les statistiques...) sont
portées par des objets `Permission` Django standards :

- celles générées automatiquement pour chaque modèle
  (`add_<modele>`, `change_<modele>`, `delete_<modele>`, `view_<modele>`) ;
- quelques permissions personnalisées déclarées dans `Meta.permissions`
  (voir `Intervention.view_all_interventions`, `.export_interventions`,
  `.view_statistics` et `SparePart.export_stock`).

Ces permissions sont regroupées dans des `Group` ("Agent bureau",
"Technicien", "Manager", ...) définis de façon déclarative dans
`core/permissions.py::ROLE_PERMISSIONS` et provisionnés par la commande
`python manage.py setup_roles` (appelée automatiquement après chaque
migration, voir `core/apps.py`).

Pourquoi ce n'est pas juste `is_staff` :
- `is_staff` est une notion Django "peut se connecter à /admin/", pas un
  rôle métier. On la garde pour ce seul usage (accès à /admin/).
- Avec un booléen unique, ajouter un 3e rôle (ex. "Manager" en lecture
  seule sur tout, sans droit de suppression) obligeait à modifier chaque
  vue. Avec des Groups/Permissions, ajouter un rôle = ajouter une entrée
  dans `ROLE_PERMISSIONS` puis relancer `setup_roles` : **aucune vue
  n'a besoin d'être modifiée**.

Ce module reste volontairement au-dessus de Django (pas de dépendance
type django-guardian) : pour ce projet, la granularité "par modèle" est
suffisante ; la seule règle réellement "par objet" — un technicien ne
touche qu'à SES interventions — est gérée par `user_can_access_intervention`
ci-dessous, indépendamment des Groups.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden


# ───────────────────────────────────────────────
# Définition déclarative des rôles
# ───────────────────────────────────────────────
# Chaque rôle est un Group Django associé à une liste de codenames de
# Permission (générées automatiquement par Django pour chaque modèle, ou
# déclarées dans Meta.permissions). `setup_roles` lit cette structure et
# la synchronise en base — c'est la SEULE source de vérité pour "qui peut
# faire quoi".

AGENT_BUREAU = "Agent bureau"
TECHNICIEN = "Technicien"
MANAGER = "Manager"
CLIENT = "Client"

ROLE_PERMISSIONS = {
    AGENT_BUREAU: [
        # Clients — CRUD complet
        "add_client", "change_client", "delete_client", "view_client",
        # Techniciens — CRUD complet
        "add_technician", "change_technician", "delete_technician", "view_technician",
        # Interventions — CRUD complet + visibilité globale
        "add_intervention", "change_intervention", "delete_intervention", "view_intervention",
        "view_all_interventions", "export_interventions", "view_statistics",
        # Stock — CRUD complet + mouvements + export
        "add_sparepart", "change_sparepart", "delete_sparepart", "view_sparepart",
        "add_stockmovement", "view_stockmovement", "export_stock",
        # Rapports, tâches, incidents, messages : ouverts à tout utilisateur
        # authentifié pour SES/LEURS interventions (cf. object-level check
        # ci-dessous) — un agent bureau y accède via view_all_interventions.
        "add_report", "change_report", "view_report",
        "add_task", "change_task", "view_task",
        "add_incident", "change_incident", "view_incident",
        "add_message", "view_message",
        # Journal d'activité
        "view_activitylog",
    ],
    TECHNICIEN: [
        # Lecture seule sur les référentiels partagés
        "view_client", "view_technician", "view_sparepart", "view_stockmovement",
        "view_intervention",
        # Peut créer/modifier ses propres rapports, tâches, incidents,
        # messages (restriction "ses interventions à lui" appliquée au
        # niveau de la vue via user_can_access_intervention, pas ici).
        "add_report", "change_report", "view_report",
        "add_task", "change_task", "view_task",
        "add_incident", "change_incident", "view_incident",
        "add_message", "view_message",
    ],
    MANAGER: [
        # Rôle de supervision en lecture seule sur tout le périmètre —
        # démontre qu'ajouter un rôle n'exige plus de toucher aux vues :
        # aucune ligne de core/views.py n'a été modifiée pour ce rôle.
        "view_client", "view_technician", "view_sparepart", "view_stockmovement",
        "view_intervention", "view_all_interventions", "view_statistics",
        "export_interventions", "export_stock", "view_activitylog",
        "view_report", "view_task", "view_incident", "view_message",
    ],
    CLIENT: [
        # Rôle externe (portail client) — volontairement TRÈS restreint :
        # pas de view_client/view_technician/view_sparepart/view_intervention
        # "génériques", pour qu'un compte client ne puisse jamais parcourir
        # les référentiels internes ou les interventions d'un autre client
        # via une vue qui ne ferait qu'un simple has_perm(). La visibilité
        # sur SES PROPRES données passe exclusivement par la règle
        # object-level `user_can_access_intervention` (voir plus bas) et
        # par les vues dédiées core/views.py::client_portal_*, qui
        # filtrent explicitement sur son propre profil Client.
        #
        # Les deux permissions ci-dessous ne sont volontairement PAS des
        # permissions "par modèle" de visibilité globale : `view_report`
        # et `view_message` sont nécessaires pour que `{% if perms... %}`
        # et le rendu des templates de rapport/messages fonctionnent une
        # fois l'accès déjà validé au niveau objet ; elles n'ouvrent seules
        # aucune liste non filtrée (aucune vue ne fait `Report.objects.all()`
        # ou `Message.objects.all()` sans restriction par ailleurs).
        "view_report", "view_message", "add_message",
    ],
}


# ───────────────────────────────────────────────
# Décorateurs de vue basés sur les permissions
# ───────────────────────────────────────────────

def perm_required(perm):
    """
    Équivalent de `django.contrib.auth.decorators.permission_required`,
    mais qui renvoie explicitement 403 (au lieu de rediriger vers login)
    lorsque l'utilisateur est connecté mais n'a pas la permission — plus
    clair pour un utilisateur authentifié qui essaie une action non
    autorisée par son rôle.

    Usage : @perm_required('core.add_client')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not request.user.has_perm(perm):
                return HttpResponseForbidden(
                    f"Accès refusé : cette action nécessite la permission « {perm} », "
                    f"qui n'est pas accordée à votre rôle."
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ───────────────────────────────────────────────
# Règle object-level : un technicien n'agit que sur SES interventions
# ───────────────────────────────────────────────

def get_technician_profile(user):
    """Retourne le profil Technician lié au user, ou None."""
    return getattr(user, 'technician_profile', None)


def get_client_profile(user):
    """Retourne le profil Client lié au user (portail client), ou None."""
    return getattr(user, 'client_profile', None)


def is_portal_client(user):
    """
    True si l'utilisateur est un client externe (a un profil Client lié)
    sans aucune visibilité interne (pas de profil Technician, pas de
    permission de gestion globale). Utilisé pour aiguiller vers le
    portail client et pour EXCLURE ce type de compte des vues internes
    (listes de clients/techniciens/stock, recherche globale, etc.) qui ne
    filtrent leurs résultats qu'à l'écriture, pas à la lecture.
    """
    return (
        user.is_authenticated
        and get_client_profile(user) is not None
        and get_technician_profile(user) is None
        and not has_global_intervention_access(user)
    )


def has_global_intervention_access(user):
    """
    True si l'utilisateur voit/gère toutes les interventions (Agent
    bureau, Manager, ou tout rôle futur auquel on assigne cette
    permission) — indépendamment de son statut is_staff.
    """
    return user.has_perm('core.view_all_interventions')


def user_can_access_intervention(user, intervention):
    """
    True si l'utilisateur peut CONSULTER cette intervention : soit il a
    une visibilité globale (permission), soit c'est SON intervention en
    tant que technicien assigné, soit c'est SON intervention en tant que
    client concerné (propriété de l'objet dans les deux cas, ce qu'aucune
    permission Django "par modèle" ne peut exprimer).

    Attention : ceci autorise la LECTURE. Un rôle de supervision en
    lecture seule (ex. Manager) satisfait cette règle sans pour autant
    avoir le droit d'écrire — voir `user_can_edit_intervention`. Un
    client satisfait aussi cette règle en lecture seule : il ne passe
    JAMAIS `user_can_edit_intervention` (voir plus bas).
    """
    if has_global_intervention_access(user):
        return True
    tech = get_technician_profile(user)
    if tech is not None and intervention.technicien_id == tech.id:
        return True
    client = get_client_profile(user)
    return client is not None and intervention.client_id == client.id


def user_can_message_intervention(user, intervention):
    """
    True si l'utilisateur peut ENVOYER UN MESSAGE sur cette intervention.

    Volontairement plus permissif que `user_can_edit_intervention` (qui
    gouverne tâches/pièces/incidents, réservés aux rôles internes) : la
    messagerie est un canal de communication, pas une action de gestion
    métier. Un client concerné par l'intervention doit pouvoir écrire à
    l'agent/technicien même s'il n'a aucun droit de modification — c'est
    précisément le rôle "Communication et collaboration ... avec les
    clients" du sujet de stage. On exige quand même la permission
    `add_message` (accordée à Agent bureau, Technicien et Client, mais
    PAS à Manager, qui reste volontairement lecture seule y compris sur
    ce canal).
    """
    if not user.has_perm('core.add_message'):
        return False
    return user_can_access_intervention(user, intervention)


def user_can_edit_intervention(user, intervention):
    """
    True si l'utilisateur peut AJOUTER/MODIFIER des données liées à cette
    intervention (tâches, messages, pièces consommées, incidents) :
    soit il gère les interventions (permission `change_intervention`,
    typiquement l'agent bureau), soit c'est SON intervention en tant que
    technicien assigné.

    Volontairement plus strict que `user_can_access_intervention` : un
    rôle qui a seulement `view_all_interventions` (ex. Manager) voit tout
    mais n'a pas automatiquement le droit d'écrire dessus — la
    visibilité n'est pas un droit de modification.
    """
    if user.has_perm('core.change_intervention'):
        return True
    tech = get_technician_profile(user)
    return tech is not None and intervention.technicien_id == tech.id


def is_field_technician(user):
    """
    True si l'utilisateur est un technicien de terrain (a un profil
    Technician lié) sans visibilité globale — utilisé pour aiguiller
    vers le tableau de bord personnel plutôt que le tableau de bord
    opérationnel global.
    """
    return get_technician_profile(user) is not None and not has_global_intervention_access(user)
