from .permissions import is_portal_client


def user_role(request):
    """
    Expose `user_role_label` dans tous les templates : le nom du (des)
    Group(s) auquel appartient l'utilisateur connecté. Contrairement à un
    badge basé sur `user.is_staff` (binaire), ceci s'adapte automatiquement
    à n'importe quel rôle ajouté dans core.permissions.ROLE_PERMISSIONS —
    aucune modification de template n'est nécessaire pour afficher un
    nouveau rôle (ex. "Manager").
    """
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}

    group_names = list(user.groups.values_list('name', flat=True))
    if group_names:
        label = " / ".join(group_names)
    elif user.is_superuser:
        label = "Administrateur"
    else:
        label = "Utilisateur"

    return {
        'user_role_label': label,
        # Permet à base.html d'afficher une navigation dédiée (portail
        # client) et de masquer les liens vers les référentiels internes,
        # en plus des vérifications côté vue (défense en profondeur).
        'is_portal_client': is_portal_client(user),
    }
