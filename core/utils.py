"""
Utilitaires métier : scoring de techniciens, analyse de description,
journal d'activité, notifications.

Tous les algorithmes ci-dessous sont des systèmes de règles pondérées
explicites — PAS de machine learning. Le sujet de stage demande un
moteur de recommandation et une analyse de description ; ces fonctions
les implémentent de manière honnête et explicable ligne par ligne.
"""

import math
import re
from django.core.mail import send_mail
from django.conf import settings
from .models import Technician, ActivityLog


# ───────────────────────────────────────────────
# 1. Moteur de recommandation de technicien
# ───────────────────────────────────────────────

def recommander_technicien(intervention):
    """
    Moteur de scoring pondéré pour recommander le meilleur technicien
    pour une intervention donnée.

    Critères pondérés :
      - disponibilité (poids 30%)
      - compétences en commun avec le type d'intervention (poids 25%)
      - expérience = nombre d'interventions terminées (poids 20%)
      - proximité géographique (poids 15%)
      - charge de travail actuelle (poids 10%)

    Retourne une liste de tuples (technicien, score) triée par score décroissant.
    """
    techniciens = Technician.objects.filter(disponible=True)
    if not techniciens:
        return []

    type_interv = intervention.type_intervention.lower()
    lat_i = intervention.latitude
    lon_i = intervention.longitude

    scores = []
    for tech in techniciens:
        score = 0.0

        # 1. Disponibilité (30%)
        if tech.disponible:
            score += 30.0

        # 2. Compétences (25%)
        specialites = tech.get_specialites_list()
        if type_interv in specialites or any(s in type_interv for s in specialites):
            score += 25.0
        elif specialites:
            score += 10.0  # a des compétences, même sans correspondance exacte

        # 3. Expérience (20%) — calculée depuis la source, pas un champ dupliqué
        total_terminees = tech.total_interventions_terminees()
        exp_score = min(total_terminees * 2, 20.0)  # plafonné à 20
        score += exp_score

        # 4. Proximité géographique (15%)
        if (
            lat_i is not None and lon_i is not None
            and tech.latitude is not None and tech.longitude is not None
        ):
            dist = haversine(lat_i, lon_i, tech.latitude, tech.longitude)
            if dist < 5:
                score += 15.0
            elif dist < 15:
                score += 10.0
            elif dist < 30:
                score += 5.0
        else:
            score += 7.5  # neutre si pas de coordonnées

        # 5. Charge actuelle (10%) — moins c'est mieux
        charge = tech.charge_actuelle()
        if charge == 0:
            score += 10.0
        elif charge == 1:
            score += 7.0
        elif charge == 2:
            score += 4.0
        else:
            score += 1.0

        scores.append((tech, round(score, 2)))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def haversine(lat1, lon1, lat2, lon2):
    """Distance en km entre deux points GPS."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ───────────────────────────────────────────────
# 2. Analyse de description (mots-clés)
# ───────────────────────────────────────────────

MOTS_URGENCE = [
    'urgence', 'critique', 'panne', 'arrêt', 'hs', 'hors service',
    'incendie', 'fuite', 'danger', 'accident', 'bloqué', 'impossible',
    'immédiat', 'maintenant', 'asap', 'grave', 'sécurité'
]

MOTS_EQUIPEMENT = [
    'serveur', 'routeur', 'switch', 'imprimante', 'ordinateur',
    'pc', 'laptop', 'écran', 'câble', 'réseau', 'wifi', 'caméra',
    'téléphone', 'ascenseur', 'climatisation', 'générateur', 'pompe',
    'convoyeur', 'broyeur', 'concasseur', 'silo', 'tapis'
]


def analyser_description(description):
    """
    Analyse la description d'une intervention pour détecter :
      - le niveau d'urgence suggéré
      - les équipements mentionnés

    Retourne un dict {'priorite_suggeree': str, 'equipements': list}
    """
    desc_lower = (description or "").lower()

    def _contient_mot(mot, texte):
        """Recherche par mot entier (\\b) plutôt que par sous-chaîne, pour
        éviter les faux positifs sur les tokens courts (ex: 'hs' ne doit
        pas matcher à l'intérieur d'un autre mot)."""
        return re.search(r'\b' + re.escape(mot) + r'\b', texte) is not None

    # Comptage des mots d'urgence
    score_urgence = sum(1 for mot in MOTS_URGENCE if _contient_mot(mot, desc_lower))

    if score_urgence >= 3:
        priorite = 'critique'
    elif score_urgence >= 2:
        priorite = 'haute'
    elif score_urgence >= 1:
        priorite = 'moyenne'
    else:
        priorite = 'basse'

    # Détection équipements
    equipements = [eq for eq in MOTS_EQUIPEMENT if _contient_mot(eq, desc_lower)]

    return {
        'priorite_suggeree': priorite,
        'equipements': equipements
    }


# ───────────────────────────────────────────────
# 3. Journal d'activité
# ───────────────────────────────────────────────

def log_activity(utilisateur, action, detail=""):
    """Enregistre une action dans le journal d'activité."""
    ActivityLog.objects.create(
        utilisateur=utilisateur,
        action=action,
        detail=detail
    )


# ───────────────────────────────────────────────
# 4. Notifications email (backend console en dev)
# ───────────────────────────────────────────────

def notifier_assignation(intervention):
    """Envoie un email au technicien quand il est assigné."""
    if intervention.technicien and intervention.technicien.email:
        send_mail(
            subject=f"[OCP Intervention] Nouvelle assignation — #{intervention.id}",
            message=(
                f"Bonjour {intervention.technicien.prenom},\n\n"
                f"Vous avez été assigné(e) à l'intervention :\n"
                f"Titre : {intervention.titre}\n"
                f"Client : {intervention.client.nom}\n"
                f"Type : {intervention.get_type_intervention_display()}\n"
                f"Priorité : {intervention.get_priorite_display()}\n\n"
                f"Connectez-vous à l'application pour plus de détails."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@ocp.ma',
            recipient_list=[intervention.technicien.email],
            fail_silently=True
        )


def notifier_terminaison(intervention):
    """Notifie le créateur quand une intervention est terminée."""
    if intervention.created_by and intervention.created_by.email:
        send_mail(
            subject=f"[OCP Intervention] Terminée — #{intervention.id}",
            message=(
                f"Bonjour,\n\n"
                f"L'intervention suivante a été marquée comme terminée :\n"
                f"Titre : {intervention.titre}\n"
                f"Technicien : {intervention.technicien or 'Non assigné'}\n"
                f"Date de fin : {intervention.date_fin.strftime('%d/%m/%Y %H:%M') if intervention.date_fin else 'N/A'}\n\n"
                f"Consultez le rapport dans l'application."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@ocp.ma',
            recipient_list=[intervention.created_by.email],
            fail_silently=True
        )