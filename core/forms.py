from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    Client, Technician, SparePart, Intervention,
    Task, Report, Message, StockMovement, Incident,ClientEvaluation
)


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full pl-11 pr-4 py-3 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:border-ocp-500 focus:ring-4 focus:ring-ocp-500/10 outline-none transition placeholder:text-slate-400',
            'placeholder': "Nom d'utilisateur",
            'autocomplete': 'username',
        }),
        label="Nom d'utilisateur"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full pl-11 pr-11 py-3 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:border-ocp-500 focus:ring-4 focus:ring-ocp-500/10 outline-none transition placeholder:text-slate-400',
            'placeholder': 'Mot de passe',
            'autocomplete': 'current-password',
        }),
        label="Mot de passe"
    )


class ClientForm(forms.ModelForm):
    """
    Formulaire client. Le champ `user` (optionnel) permet à l'agent
    bureau de lier un compte Django existant à la fiche — c'est ce lien
    qui active le portail client pour ce compte. Il doit être créé au
    préalable (ex. via /admin/) : ce formulaire ne crée pas de compte,
    il se contente de le rattacher, exactement comme TechnicianForm.
    """
    class Meta:
        model = Client
        fields = ['nom', 'email', 'telephone', 'adresse', 'secteur', 'user']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'class': 'form-input'}),
            'adresse': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'secteur': forms.TextInput(attrs={'class': 'form-input'}),
            'user': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {'user': "Compte portail client (optionnel)"}


class TechnicianForm(forms.ModelForm):
    class Meta:
        model = Technician
        fields = ['user', 'nom', 'prenom', 'email', 'telephone', 'specialites',
                  'disponible', 'localisation', 'latitude', 'longitude', 'note_moyenne']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'nom': forms.TextInput(attrs={'class': 'form-input'}),
            'prenom': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'class': 'form-input'}),
            'specialites': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Compétences séparées par des virgules'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'localisation': forms.TextInput(attrs={'class': 'form-input'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-input'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-input'}),
            'note_moyenne': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'}),
        }


class SparePartForm(forms.ModelForm):
    """
    Formulaire de pièce détachée.
    NE INCLUT PAS quantite_stock — ce champ n'est jamais modifiable
    directement (principe StockService).
    """
    class Meta:
        model = SparePart
        fields = ['nom', 'reference', 'description', 'quantite_minimale',
                  'prix_unitaire', 'fournisseur', 'emplacement']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-input'}),
            'reference': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'quantite_minimale': forms.NumberInput(attrs={'class': 'form-input'}),
            'prix_unitaire': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'fournisseur': forms.TextInput(attrs={'class': 'form-input'}),
            'emplacement': forms.TextInput(attrs={'class': 'form-input'}),
        }


def _date_planification_field():
    """
    Construit le champ `date_planification` partagé par `InterventionForm`
    et `InterventionTechnicianForm`. Déclaré explicitement (plutôt que
    laissé à Meta.widgets) : dans le contexte de l'admin Django,
    ModelAdmin.get_form() passe son propre formfield_callback
    (formfield_for_dbfield) à modelform_factory, qui ignore Meta.widgets
    pour les champs non déclarés sur la classe et transforme un
    DateTimeField en SplitDateTimeField (AdminSplitDateTime). Résultat :
    le widget datetime-local est silencieusement remplacé ET
    form.changed_data plante (SplitDateTimeField.has_changed() reçoit une
    valeur de champ non-liste). Un champ déclaré explicitement sur la
    classe est toujours prioritaire sur le formfield_callback, donc ceci
    fixe le rendu ET le crash dans les deux contextes (admin et vues
    applicatives).

    Une fonction plutôt qu'une instance de Field partagée : une instance
    de champ Django ne doit jamais être réutilisée telle quelle entre
    deux classes de formulaire (elle est mutée par le binding), donc
    chaque formulaire a besoin de sa propre instance — cette fonction
    évite simplement de dupliquer la définition (widget + format + commentaire).
    """
    return forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'class': 'form-input', 'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
    )


# Transitions de statut autorisées depuis le formulaire générique
# (création/édition). Les boutons dédiés "Démarrer" / "Terminer" (vues
# intervention_start / intervention_finish) appliquent des règles plus
# strictes encore (une seule transition précise à la fois) ; celles-ci
# couvrent le cas plus large de l'édition manuelle par l'agent (ex:
# planifier une date, annuler), tout en empêchant de sauter des étapes
# (ex: passer directement de « en attente » à « terminée », ce qui
# laissait auparavant une intervention « terminée » sans date_debut,
# sans avoir jamais été « en cours », faussant silencieusement le taux
# d'achèvement et les statistiques).
TRANSITIONS_STATUT_AUTORISEES = {
    'en_attente': {'en_attente', 'planifiee', 'annulee'},
    'planifiee': {'planifiee', 'en_cours', 'en_attente', 'annulee'},
    'en_cours': {'en_cours', 'terminee', 'annulee'},
    'terminee': {'terminee'},
    'annulee': {'annulee', 'en_attente'},
}


class StatutTransitionMixin:
    """Empêche de sauter des étapes du cycle de vie via le formulaire
    générique. À la création, le statut est toujours forcé à
    'en_attente' quel que soit ce qui est soumis : rien ne justifie de
    créer une intervention déjà « en cours » ou « terminée »."""

    def clean(self):
        cleaned_data = super().clean()
        nouveau_statut = cleaned_data.get('statut')
        if nouveau_statut is None:
            return cleaned_data

        if self.instance.pk is None:
            # Création : ignore silencieusement toute valeur soumise,
            # le cycle de vie démarre toujours à 'en_attente'.
            cleaned_data['statut'] = 'en_attente'
            return cleaned_data

        ancien_statut = self.instance.statut
        autorises = TRANSITIONS_STATUT_AUTORISEES.get(ancien_statut, {ancien_statut})
        if nouveau_statut != ancien_statut and nouveau_statut not in autorises:
            self.add_error(
                'statut',
                f"Transition impossible : « {dict(Intervention.STATUT_CHOICES).get(ancien_statut, ancien_statut)} » "
                f"→ « {dict(Intervention.STATUT_CHOICES).get(nouveau_statut, nouveau_statut)} ». "
                "Utilisez les actions dédiées (Démarrer / Terminer) pour l'avancement normal."
            )
        return cleaned_data


class InterventionForm(StatutTransitionMixin, forms.ModelForm):
    date_planification = _date_planification_field()

    class Meta:
        model = Intervention
        fields = ['titre', 'description', 'client', 'technicien', 'type_intervention',
                  'priorite', 'statut', 'date_planification', 'duree_estimee',
                  'localisation', 'latitude', 'longitude']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'technicien': forms.Select(attrs={'class': 'form-select'}),
            'type_intervention': forms.Select(attrs={'class': 'form-select'}),
            'priorite': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'duree_estimee': forms.NumberInput(attrs={'class': 'form-input'}),
            'localisation': forms.TextInput(attrs={'class': 'form-input'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-input'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-input'}),
        }


class InterventionTechnicianForm(StatutTransitionMixin, forms.ModelForm):
    """Formulaire restreint pour les techniciens (pas de modification client/technicien)."""
    date_planification = _date_planification_field()

    class Meta:
        model = Intervention
        fields = ['titre', 'description', 'type_intervention', 'priorite',
                  'statut', 'date_planification', 'duree_estimee',
                  'localisation', 'latitude', 'longitude']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'type_intervention': forms.Select(attrs={'class': 'form-select'}),
            'priorite': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'duree_estimee': forms.NumberInput(attrs={'class': 'form-input'}),
            'localisation': forms.TextInput(attrs={'class': 'form-input'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-input'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-input'}),
        }


class InterventionAssignForm(forms.Form):
    """
    Formulaire dédié à l'assignation/réassignation d'un technicien à une
    intervention — choix libre parmi TOUS les techniciens (pas seulement
    les 3 recommandés par le moteur de scoring), utilisé depuis la page
    de détail pour permettre à l'agent bureau de choisir explicitement
    qui il veut affecter.
    """
    technicien = forms.ModelChoiceField(
        queryset=Technician.objects.all().order_by('nom', 'prenom'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Technicien",
        empty_label="— Choisir un technicien —",
    )


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['titre', 'description', 'statut']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
        }


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['contenu', 'observations', 'recommandations', 'satisfaction_client']
        widgets = {
            'contenu': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 6}),
            'observations': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'recommandations': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'satisfaction_client': forms.Select(attrs={'class': 'form-select'}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['contenu']
        widgets = {
            'contenu': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Votre message...'
            }),
        }


class StockMovementForm(forms.ModelForm):
    """Formulaire de mouvement de stock (réservé aux agents bureau)."""
    class Meta:
        model = StockMovement
        fields = ['piece', 'type_mouvement', 'quantite', 'raison']
        widgets = {
            'piece': forms.Select(attrs={'class': 'form-select'}),
            'type_mouvement': forms.Select(attrs={'class': 'form-select'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-input'}),
            'raison': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }


class InterventionPieceForm(forms.Form):
    """Formulaire pour associer une pièce à une intervention (consommation)."""
    piece = forms.ModelChoiceField(
        queryset=SparePart.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Pièce"
    )
    quantite = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-input'}),
        label="Quantité"
    )


class IncidentForm(forms.ModelForm):
    """Formulaire de signalement d'incident sur une intervention."""
    class Meta:
        model = Incident
        fields = ['titre', 'description', 'gravite']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': "Ex: Panne électrique imprévue"}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'gravite': forms.Select(attrs={'class': 'form-select'}),
        }

class ClientEvaluationForm(forms.ModelForm):
    """Formulaire d'évaluation client (note intervention /5 + technicien /100)."""
    class Meta:
        model = ClientEvaluation
        fields = ['note_intervention', 'note_technicien', 'commentaire']
        widgets = {
            'note_intervention': forms.RadioSelect(),
            'note_technicien': forms.NumberInput(attrs={
                'class': 'form-input', 'min': 0, 'max': 100, 'placeholder': 'Ex : 85'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 3,
                'placeholder': "Un commentaire sur l'intervention (optionnel)"
            }),
        }
        labels = {
            'note_intervention': "Note de l'intervention",
            'note_technicien': "Note du technicien",
            'commentaire': "Commentaire",
        }