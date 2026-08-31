from django.contrib import admin
from .models import (
    Client, Technician, SparePart, Intervention,
    InterventionPiece, Task, Report, Message,
    StockMovement, ActivityLog, Incident, ClientEvaluation
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['nom', 'email', 'telephone', 'secteur', 'user', 'created_at']
    search_fields = ['nom', 'email', 'telephone']
    list_filter = ['secteur']
    autocomplete_fields = ['user']


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ['prenom', 'nom', 'email', 'disponible', 'note_moyenne']
    search_fields = ['nom', 'prenom', 'email', 'specialites']
    list_filter = ['disponible']


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ['nom', 'reference', 'quantite_stock', 'quantite_minimale', 'prix_unitaire', 'fournisseur']
    search_fields = ['nom', 'reference', 'fournisseur']
    list_filter = ['fournisseur']
    readonly_fields = ['quantite_stock']


class InterventionPieceInline(admin.TabularInline):
    model = InterventionPiece
    extra = 0


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0


class IncidentInline(admin.TabularInline):
    model = Incident
    extra = 0


@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    list_display = ['id', 'titre', 'client', 'technicien', 'type_intervention', 'priorite', 'statut', 'date_creation']
    list_filter = ['type_intervention', 'priorite', 'statut']
    search_fields = ['titre', 'description', 'client__nom']
    inlines = [TaskInline, InterventionPieceInline, IncidentInline]
    date_hierarchy = 'date_creation'


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['titre', 'intervention', 'gravite', 'resolu', 'signale_par', 'date_signalement']
    list_filter = ['gravite', 'resolu']
    search_fields = ['titre', 'description', 'intervention__titre']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['titre', 'intervention', 'statut', 'created_at']
    list_filter = ['statut']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['intervention', 'satisfaction_client', 'created_at']
    search_fields = ['intervention__titre']


@admin.register(ClientEvaluation)
class ClientEvaluationAdmin(admin.ModelAdmin):
    list_display = ['intervention', 'note_intervention', 'note_technicien', 'date_evaluation']
    list_filter = ['note_intervention']
    search_fields = ['intervention__titre', 'commentaire']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['expediteur', 'intervention', 'date_envoi']
    search_fields = ['contenu']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['piece', 'type_mouvement', 'quantite', 'utilisateur', 'date_mouvement']
    list_filter = ['type_mouvement']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'utilisateur', 'date']
    list_filter = ['date']