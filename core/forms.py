from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    Client, Technician, SparePart, Intervention,
    Task, Report, Message, StockMovement, Incident
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


class InterventionForm(forms.ModelForm):
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
            'date_planification': forms.DateTimeInput(
                attrs={'class': 'form-input', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'duree_estimee': forms.NumberInput(attrs={'class': 'form-input'}),
            'localisation': forms.TextInput(attrs={'class': 'form-input'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-input'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-input'}),
        }


class InterventionTechnicianForm(forms.ModelForm):
    """Formulaire restreint pour les techniciens (pas de modification client/technicien)."""
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
            'date_planification': forms.DateTimeInput(
                attrs={'class': 'form-input', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
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
