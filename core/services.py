"""
Service centralisé de gestion des stocks.

Principe de conception : quantite_stock ne doit JAMAIS être modifiée
par un formulaire direct. Toute variation de stock passe obligatoirement
par StockService.adjust() qui :
  1. Crée systématiquement un StockMovement (traçabilité complète)
  2. Refuse une sortie si le stock est insuffisant
  3. Met à jour le champ quantite_stock de manière atomique

Cela corrige l'erreur v1 où le stock était modifiable par trois chemins
différents, deux sans historique, entraînant des dérives silencieuses.
"""

from django.db import transaction
from .models import SparePart, StockMovement


class StockService:
    @staticmethod
    @transaction.atomic
    def adjust(piece, type_mouvement, quantite, raison="", utilisateur=None):
        """
        Ajuste le stock d'une pièce de manière centralisée.

        Args:
            piece: instance SparePart
            type_mouvement: 'entree' ou 'sortie'
            quantite: quantité positive
            raison: description du mouvement
            utilisateur: instance User (optionnel)

        Returns:
            StockMovement instance

        Raises:
            ValueError: si stock insuffisant pour une sortie
        """
        if quantite <= 0:
            raise ValueError("La quantité doit être positive.")

        # Verrouille la ligne en base (SELECT ... FOR UPDATE) et relit la
        # valeur la plus récente avant de calculer le nouveau stock, pour
        # éviter une perte de mise à jour si deux mouvements arrivent en
        # même temps (ex: deux agents qui enregistrent une sortie au même
        # moment sur la même pièce).
        piece = SparePart.objects.select_for_update().get(pk=piece.pk)

        if type_mouvement == 'sortie':
            if piece.quantite_stock < quantite:
                raise ValueError(
                    f"Stock insuffisant pour {piece.nom}. "
                    f"Disponible : {piece.quantite_stock}, demandé : {quantite}"
                )
            piece.quantite_stock -= quantite
        elif type_mouvement == 'entree':
            piece.quantite_stock += quantite
        else:
            raise ValueError("Type de mouvement invalide. Utiliser 'entree' ou 'sortie'.")

        piece.save()

        mouvement = StockMovement.objects.create(
            piece=piece,
            type_mouvement=type_mouvement,
            quantite=quantite,
            raison=raison,
            utilisateur=utilisateur
        )
        return mouvement

    @staticmethod
    def consommer_pour_intervention(intervention, piece, quantite, utilisateur=None):
        """Sortie de stock liée à une intervention."""
        raison = f"Utilisation sur intervention #{intervention.id} — {intervention.titre}"
        return StockService.adjust(piece, 'sortie', quantite, raison, utilisateur)
