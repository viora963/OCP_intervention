from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Client(models.Model):
    # user est optionnel : un Client existe d'abord comme fiche gérée par
    # l'agent bureau (cf. limite historique documentée dans le README).
    # Le lier à un compte est ce qui active le portail client (lecture
    # seule sur SES interventions + messagerie), selon le même principe
    # que Technician.user ci-dessous — même optionalité, même
    # indépendance des champs métier vis-à-vis du compte d'authentification.
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_profile',
        verbose_name="Compte utilisateur (portail client)"
    )
    nom = models.CharField(max_length=200, verbose_name="Nom")
    email = models.EmailField(blank=True, verbose_name="Email")
    telephone = models.CharField(max_length=50, blank=True, verbose_name="Téléphone")
    adresse = models.TextField(blank=True, verbose_name="Adresse")
    secteur = models.CharField(max_length=200, blank=True, verbose_name="Secteur")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        ordering = ['nom']
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self):
        return self.nom


class Technician(models.Model):
    # user est optionnel et sert UNIQUEMENT à l'authentification.
    # Les champs nom/prenom/email/telephone du Technician ne sont PAS
    # synchronisés automatiquement avec le User lié. C'est un choix
    # délibéré : un technicien peut exister sans compte (fiche RH),
    # et ses données métier restent indépendantes du système d'auth.
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='technician_profile',
        verbose_name="Compte utilisateur"
    )
    nom = models.CharField(max_length=100, verbose_name="Nom")
    prenom = models.CharField(max_length=100, verbose_name="Prénom")
    email = models.EmailField(blank=True, verbose_name="Email")
    telephone = models.CharField(max_length=50, blank=True, verbose_name="Téléphone")
    specialites = models.TextField(
        blank=True,
        help_text="Compétences séparées par des virgules",
        verbose_name="Spécialités"
    )
    disponible = models.BooleanField(default=True, verbose_name="Disponible")
    localisation = models.CharField(max_length=300, blank=True, verbose_name="Localisation")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Longitude")
    note_moyenne = models.FloatField(default=0.0, verbose_name="Note moyenne")

    class Meta:
        ordering = ['nom', 'prenom']
        verbose_name = "Technicien"
        verbose_name_plural = "Techniciens"

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    # NE PAS stocker ce compte dans un champ séparé — le dériver de la source.
    def total_interventions_terminees(self):
        return self.intervention_set.filter(statut='terminee').count()

    def charge_actuelle(self):
        """Nombre d'interventions actives (planifiée ou en cours)."""
        return self.intervention_set.filter(statut__in=['planifiee', 'en_cours']).count()

    def get_specialites_list(self):
        return [s.strip().lower() for s in self.specialites.split(',') if s.strip()]


class SparePart(models.Model):
    nom = models.CharField(max_length=200, verbose_name="Nom")
    reference = models.CharField(max_length=100, unique=True, verbose_name="Référence")
    description = models.TextField(blank=True, verbose_name="Description")
    # quantite_stock ne doit JAMAIS être modifiable par un formulaire direct.
    # Voir StockService : c'est un principe de conception central.
    quantite_stock = models.IntegerField(default=0, verbose_name="Quantité en stock")
    quantite_minimale = models.IntegerField(default=5, verbose_name="Quantité minimale")
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Prix unitaire")
    fournisseur = models.CharField(max_length=200, blank=True, verbose_name="Fournisseur")
    emplacement = models.CharField(max_length=200, blank=True, verbose_name="Emplacement")

    class Meta:
        ordering = ['nom']
        verbose_name = "Pièce détachée"
        verbose_name_plural = "Pièces détachées"
        permissions = [
            ('export_stock', "Peut exporter le stock en CSV"),
        ]

    def __str__(self):
        return f"{self.nom} ({self.reference})"

    def est_sous_seuil(self):
        return self.quantite_stock <= self.quantite_minimale

    def valeur_stock(self):
        return self.quantite_stock * self.prix_unitaire


class Intervention(models.Model):
    TYPE_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('reparation', 'Réparation'),
        ('installation', 'Installation'),
        ('urgence', 'Urgence'),
        ('inspection', 'Inspection'),
    ]
    PRIORITE_CHOICES = [
        ('basse', 'Basse'),
        ('moyenne', 'Moyenne'),
        ('haute', 'Haute'),
        ('critique', 'Critique'),
    ]
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('planifiee', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]

    titre = models.CharField(max_length=300, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='interventions', verbose_name="Client")
    technicien = models.ForeignKey(
        Technician,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intervention_set',
        verbose_name="Technicien"
    )
    type_intervention = models.CharField(max_length=50, choices=TYPE_CHOICES, default='maintenance', verbose_name="Type")
    priorite = models.CharField(max_length=50, choices=PRIORITE_CHOICES, default='moyenne', verbose_name="Priorité")
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='en_attente', verbose_name="Statut")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_planification = models.DateTimeField(null=True, blank=True, verbose_name="Date de planification")
    date_debut = models.DateTimeField(null=True, blank=True, verbose_name="Date de début")
    date_fin = models.DateTimeField(null=True, blank=True, verbose_name="Date de fin")
    duree_estimee = models.IntegerField(
        default=60,
        help_text="Durée estimée en minutes",
        verbose_name="Durée estimée (min)"
    )
    localisation = models.CharField(max_length=300, blank=True, verbose_name="Localisation")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Longitude")
    pieces_utilisees = models.ManyToManyField(
        SparePart,
        through='InterventionPiece',
        blank=True,
        verbose_name="Pièces utilisées"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interventions_creees',
        verbose_name="Créé par"
    )

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Intervention"
        verbose_name_plural = "Interventions"
        permissions = [
            # Permissions personnalisées (en plus des add/change/delete/view
            # générés automatiquement par Django). Elles sont assignées à des
            # Group ("Agent bureau", "Technicien", "Manager", ...) par la
            # commande `setup_roles` — voir core/permissions.py.
            ('view_all_interventions',
             "Peut voir/gérer toutes les interventions (pas seulement les siennes)"),
            ('export_interventions',
             "Peut exporter les interventions en CSV"),
            ('view_statistics',
             "Peut consulter la page de statistiques détaillées"),
        ]

    def __str__(self):
        return f"#{self.id} — {self.titre}"

    def duree_reelle(self):
        """Durée réelle en minutes, si l'intervention est terminée."""
        if self.date_debut and self.date_fin:
            delta = self.date_fin - self.date_debut
            return int(delta.total_seconds() / 60)
        return None

    def est_en_retard(self):
        """Vrai si planifiée et date_planification dépassée sans début."""
        if self.statut in ['en_attente', 'planifiee'] and self.date_planification:
            return timezone.now() > self.date_planification
        return False

    def save(self, *args, **kwargs):
        # date_debut se remplit automatiquement au passage en 'en_cours'
        if self.statut == 'en_cours' and not self.date_debut:
            self.date_debut = timezone.now()
        # date_fin se remplit automatiquement au passage en 'terminee'
        if self.statut == 'terminee' and not self.date_fin:
            self.date_fin = timezone.now()
        super().save(*args, **kwargs)


class InterventionPiece(models.Model):
    intervention = models.ForeignKey(Intervention, on_delete=models.CASCADE, verbose_name="Intervention")
    piece = models.ForeignKey(SparePart, on_delete=models.CASCADE, verbose_name="Pièce")
    quantite = models.PositiveIntegerField(default=1, verbose_name="Quantité")
    date_utilisation = models.DateTimeField(auto_now_add=True, verbose_name="Date d'utilisation")

    class Meta:
        unique_together = ('intervention', 'piece')
        verbose_name = "Pièce utilisée"
        verbose_name_plural = "Pièces utilisées"

    def __str__(self):
        return f"{self.piece.nom} x{self.quantite} — {self.intervention}"


class Task(models.Model):
    STATUT_CHOICES = [
        ('a_faire', 'À faire'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
    ]
    intervention = models.ForeignKey(Intervention, on_delete=models.CASCADE, related_name='tasks', verbose_name="Intervention")
    titre = models.CharField(max_length=300, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='a_faire', verbose_name="Statut")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        ordering = ['created_at']
        verbose_name = "Tâche"
        verbose_name_plural = "Tâches"

    def __str__(self):
        return self.titre


class Report(models.Model):
    intervention = models.OneToOneField(
        Intervention,
        on_delete=models.CASCADE,
        related_name='report',
        verbose_name="Intervention"
    )
    contenu = models.TextField(blank=True, verbose_name="Contenu du rapport")
    observations = models.TextField(blank=True, verbose_name="Observations")
    recommandations = models.TextField(blank=True, verbose_name="Recommandations")
    satisfaction_client = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        null=True,
        blank=True,
        verbose_name="Satisfaction client (1-5)"
    )
    # Champs auto-générés par règles métier (PAS de machine learning).
    # Le nom 'ai_summary' est conservé pour compatibilité modèle mais
    # l'UI ne présente JAMAIS cela comme de l'IA.
    ai_summary = models.TextField(blank=True, verbose_name="Résumé automatique")
    ai_anomalies = models.TextField(blank=True, verbose_name="Anomalies détectées")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Rapport"
        verbose_name_plural = "Rapports"

    def __str__(self):
        return f"Rapport — {self.intervention}"

    def generer_resume(self):
        """Génère un résumé basé sur des règles métier (pas d'IA)."""
        lignes = []
        lignes.append(f"Intervention : {self.intervention.titre}")
        lignes.append(f"Client : {self.intervention.client.nom}")
        if self.intervention.technicien:
            lignes.append(f"Technicien : {self.intervention.technicien}")
        lignes.append(f"Type : {self.intervention.get_type_intervention_display()}")
        lignes.append(f"Statut : {self.intervention.get_statut_display()}")
        duree = self.intervention.duree_reelle()
        if duree is not None:
            lignes.append(f"Durée réelle : {duree} min (estimée : {self.intervention.duree_estimee} min)")
        taches = self.intervention.tasks.all()
        if taches:
            terminees = [t for t in taches if t.statut == 'terminee']
            lignes.append(f"Tâches réalisées : {len(terminees)}/{len(taches)}")
            if terminees:
                lignes.append("  - " + "\n  - ".join(t.titre for t in terminees))
        pieces = self.intervention.interventionpiece_set.all()
        if pieces:
            lignes.append(f"Pièces utilisées : {', '.join([f'{p.piece.nom} (x{p.quantite})' for p in pieces])}")
        incidents = self.intervention.incidents.all()
        if incidents:
            lignes.append(f"Incidents signalés : {incidents.count()}")
        self.ai_summary = "\n".join(lignes)

    def detecter_anomalies(self):
        """Détecte des anomalies par règles simples (pas d'IA)."""
        anomalies = []
        if self.intervention.est_en_retard():
            anomalies.append("L'intervention est en retard par rapport à la date de planification.")
        duree = self.intervention.duree_reelle()
        if duree and self.intervention.duree_estimee > 0:
            ecart = abs(duree - self.intervention.duree_estimee) / self.intervention.duree_estimee
            if ecart > 0.5:
                anomalies.append(f"Écart important entre durée estimée ({self.intervention.duree_estimee} min) et réelle ({duree} min).")
        if self.satisfaction_client and self.satisfaction_client <= 2:
            anomalies.append(f"Satisfaction client faible ({self.satisfaction_client}/5).")
        incidents_non_resolus = self.intervention.incidents.filter(resolu=False)
        if incidents_non_resolus.exists():
            anomalies.append(
                f"{incidents_non_resolus.count()} incident(s) non résolu(s) sur cette intervention."
            )
        incidents_majeurs = self.intervention.incidents.filter(gravite__in=['majeure', 'critique'])
        if incidents_majeurs.exists():
            anomalies.append(
                f"{incidents_majeurs.count()} incident(s) de gravité majeure/critique signalé(s)."
            )
        self.ai_anomalies = "\n".join(anomalies) if anomalies else "Aucune anomalie détectée."

    def generer_complet(self):
        self.generer_resume()
        self.detecter_anomalies()
        self.save()


class Message(models.Model):
    intervention = models.ForeignKey(Intervention, on_delete=models.CASCADE, related_name='messages', verbose_name="Intervention")
    expediteur = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Expéditeur")
    contenu = models.TextField(verbose_name="Contenu")
    date_envoi = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")

    class Meta:
        ordering = ['date_envoi']
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"Message de {self.expediteur.username} — {self.intervention}"


class StockMovement(models.Model):
    TYPE_CHOICES = [
        ('entree', 'Entrée'),
        ('sortie', 'Sortie'),
    ]
    piece = models.ForeignKey(SparePart, on_delete=models.CASCADE, related_name='mouvements', verbose_name="Pièce")
    type_mouvement = models.CharField(max_length=50, choices=TYPE_CHOICES, verbose_name="Type de mouvement")
    quantite = models.PositiveIntegerField(verbose_name="Quantité")
    raison = models.TextField(blank=True, verbose_name="Raison")
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Utilisateur")
    date_mouvement = models.DateTimeField(auto_now_add=True, verbose_name="Date du mouvement")

    class Meta:
        ordering = ['-date_mouvement']
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"

    def __str__(self):
        return f"{self.get_type_mouvement_display()} — {self.piece.nom} x{self.quantite}"


class ActivityLog(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Utilisateur")
    action = models.CharField(max_length=200, verbose_name="Action")
    detail = models.TextField(blank=True, verbose_name="Détail")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Date")

    class Meta:
        ordering = ['-date']
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journal d'activité"

    def __str__(self):
        return f"{self.action} — {self.date.strftime('%d/%m/%Y %H:%M')}"


class Incident(models.Model):
    """
    Incident rencontré sur le terrain pendant une intervention.
    Répond au point 'suivi en temps réel ... les éventuels incidents
    rencontrés' du sujet de stage — jusqu'ici seul l'avancement du
    statut était suivi, sans notion distincte d'incident.
    """
    GRAVITE_CHOICES = [
        ('mineure', 'Mineure'),
        ('moderee', 'Modérée'),
        ('majeure', 'Majeure'),
        ('critique', 'Critique'),
    ]

    intervention = models.ForeignKey(
        Intervention,
        on_delete=models.CASCADE,
        related_name='incidents',
        verbose_name="Intervention"
    )
    titre = models.CharField(max_length=300, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    gravite = models.CharField(max_length=50, choices=GRAVITE_CHOICES, default='mineure', verbose_name="Gravité")
    signale_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents_signales',
        verbose_name="Signalé par"
    )
    resolu = models.BooleanField(default=False, verbose_name="Résolu")
    date_signalement = models.DateTimeField(auto_now_add=True, verbose_name="Date de signalement")
    date_resolution = models.DateTimeField(null=True, blank=True, verbose_name="Date de résolution")

    class Meta:
        ordering = ['-date_signalement']
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"

    def __str__(self):
        return f"{self.titre} — {self.intervention}"

    def save(self, *args, **kwargs):
        if self.resolu and not self.date_resolution:
            self.date_resolution = timezone.now()
        if not self.resolu:
            self.date_resolution = None
        super().save(*args, **kwargs)
