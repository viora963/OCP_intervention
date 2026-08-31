import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db import transaction
from django.db.models import Count, Avg, Q, F, Value
from django.db.models.functions import TruncDate, Concat
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from django.utils.http import urlencode

try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False

from .models import (
    Client, Technician, SparePart, Intervention, InterventionPiece,
    Task, Report, Message, StockMovement, ActivityLog, Incident, ClientEvaluation
)
from .forms import (
    LoginForm, ClientForm, TechnicianForm, SparePartForm,
    InterventionForm, InterventionTechnicianForm, InterventionAssignForm,
    TaskForm, ReportForm, MessageForm, StockMovementForm,
    InterventionPieceForm, IncidentForm, ClientEvaluationForm
)
from .services import StockService
from .utils import (
    recommander_technicien, analyser_description,
    log_activity, notifier_assignation, notifier_terminaison
)
from .permissions import (
    perm_required, get_technician_profile,
    has_global_intervention_access, user_can_access_intervention,
    user_can_edit_intervention, is_field_technician,
    get_client_profile, is_portal_client, user_can_message_intervention,
)


# ───────────────────────────────────────────────
# Authentification
# ───────────────────────────────────────────────

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            log_activity(user, "Connexion")
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        log_activity(request.user, "Déconnexion")
    logout(request)
    return redirect('login')


# ───────────────────────────────────────────────
# Tableaux de bord
# ───────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    Redirige vers le bon tableau de bord selon le rôle.
    - Agent bureau / Manager (permission `view_all_interventions`) :
      tableau de bord global (opérationnel).
    - Technicien de terrain (profil Technician, sans visibilité globale) :
      tableau de bord personnel.
    - Client externe (profil Client, sans visibilité globale) :
      portail client (redirection).
    """
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')
    if is_field_technician(request.user):
        return dashboard_technician(request)
    return dashboard_staff(request)


def dashboard_staff(request):
    """Tableau de bord global — vue opérationnelle (compteurs, alertes, récent)."""
    total_interventions = Intervention.objects.count()
    interventions_terminees = Intervention.objects.filter(statut='terminee').count()
    interventions_en_cours = Intervention.objects.filter(statut='en_cours').count()
    interventions_en_attente = Intervention.objects.filter(statut='en_attente').count()
    interventions_planifiees = Intervention.objects.filter(statut='planifiee').count()
    interventions_annulees = Intervention.objects.filter(statut='annulee').count()
    interventions_retard = [i for i in Intervention.objects.filter(statut__in=['en_attente', 'planifiee']) if i.est_en_retard()]

    total_techniciens = Technician.objects.count()
    techniciens_disponibles = Technician.objects.filter(disponible=True).count()

    total_clients = Client.objects.count()

    # Alertes stock sous seuil
    alertes_stock = SparePart.objects.filter(quantite_stock__lte=F('quantite_minimale'))[:5]

    # Incidents non résolus
    incidents_non_resolus = Incident.objects.filter(resolu=False).select_related('intervention')
    total_incidents_non_resolus = incidents_non_resolus.count()
    incidents_critiques = incidents_non_resolus.filter(gravite='critique').count()
    dernieres_incidents_non_resolus = incidents_non_resolus.order_by('-date_signalement')[:5]

    # Dernières interventions
    dernieres_interventions = Intervention.objects.select_related('client', 'technicien')[:10]

    # Dernières activités
    dernieres_activites = ActivityLog.objects.select_related('utilisateur')[:10]

    context = {
        'total_interventions': total_interventions,
        'interventions_terminees': interventions_terminees,
        'interventions_en_cours': interventions_en_cours,
        'interventions_en_attente': interventions_en_attente,
        'interventions_planifiees': interventions_planifiees,
        'interventions_annulees': interventions_annulees,
        'interventions_retard': interventions_retard,
        'total_techniciens': total_techniciens,
        'techniciens_disponibles': techniciens_disponibles,
        'total_clients': total_clients,
        'alertes_stock': alertes_stock,
        'dernieres_interventions': dernieres_interventions,
        'dernieres_activites': dernieres_activites,
        'total_incidents_non_resolus': total_incidents_non_resolus,
        'incidents_critiques': incidents_critiques,
        'dernieres_incidents_non_resolus': dernieres_incidents_non_resolus,
        'taux_completion': round((interventions_terminees / total_interventions) * 100) if total_interventions else 0,
    }
    return render(request, 'core/dashboard.html', context)


def dashboard_technician(request):
    """Tableau de bord personnel du technicien."""
    try:
        tech = request.user.technician_profile
    except Technician.DoesNotExist:
        django_messages.error(request, "Votre compte n'est pas lié à un profil technicien.")
        return render(request, 'core/technician_dashboard.html', {'error': True})

    mes_interventions_actives = Intervention.objects.filter(
        technicien=tech,
        statut__in=['planifiee', 'en_cours']
    ).select_related('client')

    prochaine_intervention = Intervention.objects.filter(
        technicien=tech,
        statut='planifiee'
    ).order_by('date_planification').first()

    total_terminees = tech.total_interventions_terminees()

    context = {
        'technicien': tech,
        'mes_interventions_actives': mes_interventions_actives,
        'prochaine_intervention': prochaine_intervention,
        'total_terminees': total_terminees,
    }
    return render(request, 'core/technician_dashboard.html', context)

# ───────────────────────────────────────────────
# Suivi en temps réel
# ───────────────────────────────────────────────

@perm_required('core.view_all_interventions')
def suivi_temps_reel(request):
    """Page de supervision temps réel (carte + listes), chargée une fois ;
    le contenu dynamique est ensuite alimenté par suivi_temps_reel_data."""
    return render(request, 'core/suivi_temps_reel.html', {
        'refresh_interval_ms': 8000,
    })


@perm_required('core.view_all_interventions')
def suivi_temps_reel_data(request):
    """Endpoint JSON interrogé en polling par la page de suivi temps réel."""
    now = timezone.now()

    interventions_qs = Intervention.objects.filter(
        statut__in=['en_attente', 'planifiee', 'en_cours']
    ).select_related('client', 'technicien').prefetch_related('tasks')

    interventions = []
    for i in interventions_qs:
        taches = list(i.tasks.all())
        elapsed = None
        if i.statut == 'en_cours' and i.date_debut:
            elapsed = int((now - i.date_debut).total_seconds() / 60)
        interventions.append({
            'id': i.id,
            'titre': i.titre,
            'client': i.client.nom,
            'technicien': str(i.technicien) if i.technicien else None,
            'technicien_id': i.technicien_id,
            'statut': i.statut,
            'statut_display': i.get_statut_display(),
            'priorite': i.priorite,
            'priorite_display': i.get_priorite_display(),
            'localisation': i.localisation,
            'elapsed_minutes': elapsed,
            'duree_estimee': i.duree_estimee,
            'tasks_done': len([t for t in taches if t.statut == 'terminee']),
            'tasks_total': len(taches),
            'en_retard': i.est_en_retard(),
        })

    techniciens = []
    for t in Technician.objects.all():
        techniciens.append({
            'id': t.id,
            'nom': str(t),
            'disponible': t.disponible,
            'localisation': t.localisation,
            'charge': t.charge_actuelle(),
        })

    incidents_qs = Incident.objects.filter(resolu=False).select_related('intervention').order_by('-date_signalement')[:20]
    incidents = [{
        'id': inc.id,
        'titre': inc.titre,
        'gravite': inc.gravite,
        'gravite_display': inc.get_gravite_display(),
        'intervention_id': inc.intervention_id,
        'intervention_titre': inc.intervention.titre,
        'date_signalement': inc.date_signalement.strftime('%d/%m %H:%M'),
    } for inc in incidents_qs]

    data = {
        'generated_at': now.strftime('%d/%m/%Y %H:%M:%S'),
        'counters': {
            'en_cours': sum(1 for i in interventions if i['statut'] == 'en_cours'),
            'planifiees': sum(1 for i in interventions if i['statut'] == 'planifiee'),
            'techniciens_dispo': sum(1 for t in techniciens if t['disponible']),
            'techniciens_total': len(techniciens),
            'incidents_non_resolus': len(incidents),
        },
        'interventions': interventions,
        'techniciens': techniciens,
        'incidents': incidents,
    }
    return JsonResponse(data)


# ───────────────────────────────────────────────
# Clients
# ───────────────────────────────────────────────

@login_required
def client_list(request):
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')
    q = request.GET.get('q', '')
    clients = Client.objects.filter(
        Q(nom__icontains=q) | Q(email__icontains=q) | Q(secteur__icontains=q)
    ).annotate(intervention_count=Count('interventions')).order_by('nom')

    paginator = Paginator(clients, 20)
    page = request.GET.get('page')
    clients = paginator.get_page(page)

    return render(request, 'core/client_list.html', {
        'clients': clients,
        'q': q,
        'can_manage': request.user.has_perm('core.change_client')
    })

@perm_required('core.add_client')
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            log_activity(request.user, "Création client", f"Client: {client.nom}")
            django_messages.success(request, "Client créé avec succès.")
            return redirect('client_list')
    else:
        form = ClientForm()
    return render(request, 'core/client_form.html', {'form': form, 'title': 'Nouveau client'})

@perm_required('core.change_client')
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            log_activity(request.user, "Modification client", f"Client: {client.nom}")
            return redirect('client_list')
    else:
        form = ClientForm(instance=client)
    return render(request, 'core/client_form.html', {'form': form, 'title': 'Modifier client'})

@perm_required('core.delete_client')
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        nom = client.nom
        client.delete()
        log_activity(request.user, "Suppression client", f"Client: {nom}")
        return redirect('client_list')
    return render(request, 'core/client_confirm_delete.html', {'client': client})

@login_required
def client_detail(request, pk):
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')
    client = get_object_or_404(Client, pk=pk)
    interventions = client.interventions.select_related('technicien').all()
    return render(request, 'core/client_detail.html', {
        'client': client,
        'interventions': interventions
    })


# ───────────────────────────────────────────────
# Techniciens
# ───────────────────────────────────────────────

@login_required
def technician_list(request):
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')
    q = request.GET.get('q', '')
    techs = Technician.objects.filter(
        Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(specialites__icontains=q)
    ).annotate(intervention_count=Count('intervention_set')).order_by('nom', 'prenom')

    paginator = Paginator(techs, 20)
    page = request.GET.get('page')
    techs = paginator.get_page(page)

    return render(request, 'core/technician_list.html', {
        'technicians': techs,
        'q': q,
        'can_manage': request.user.has_perm('core.change_technician')
    })

@perm_required('core.add_technician')
def technician_create(request):
    if request.method == 'POST':
        form = TechnicianForm(request.POST)
        if form.is_valid():
            tech = form.save()
            log_activity(request.user, "Création technicien", f"Technicien: {tech}")
            return redirect('technician_list')
    else:
        form = TechnicianForm()
    return render(request, 'core/technician_form.html', {'form': form, 'title': 'Nouveau technicien'})

@perm_required('core.change_technician')
def technician_edit(request, pk):
    tech = get_object_or_404(Technician, pk=pk)
    if request.method == 'POST':
        form = TechnicianForm(request.POST, instance=tech)
        if form.is_valid():
            form.save()
            log_activity(request.user, "Modification technicien", f"Technicien: {tech}")
            return redirect('technician_list')
    else:
        form = TechnicianForm(instance=tech)
    return render(request, 'core/technician_form.html', {'form': form, 'title': 'Modifier technicien'})

@perm_required('core.delete_technician')
def technician_delete(request, pk):
    tech = get_object_or_404(Technician, pk=pk)
    if request.method == 'POST':
        nom = str(tech)
        tech.delete()
        log_activity(request.user, "Suppression technicien", f"Technicien: {nom}")
        return redirect('technician_list')
    return render(request, 'core/technician_confirm_delete.html', {'technician': tech})

@login_required
def technician_detail(request, pk):
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')
    tech = get_object_or_404(Technician, pk=pk)
    interventions = tech.intervention_set.select_related('client').all()
    return render(request, 'core/technician_detail.html', {
        'technician': tech,
        'interventions': interventions
    })


# ───────────────────────────────────────────────
# Interventions
# ───────────────────────────────────────────────

@login_required
def intervention_list(request):
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')
    q = request.GET.get('q', '')
    statut = request.GET.get('statut', '')
    priorite = request.GET.get('priorite', '')
    type_i = request.GET.get('type', '')

    interventions = Intervention.objects.select_related('client', 'technicien')

    if not has_global_intervention_access(request.user):
        tech = get_technician_profile(request.user)
        interventions = interventions.filter(technicien=tech) if tech else Intervention.objects.none()

    if q:
        interventions = interventions.filter(
            Q(titre__icontains=q) | Q(description__icontains=q) |
            Q(client__nom__icontains=q)
        )
    if statut:
        interventions = interventions.filter(statut=statut)
    if priorite:
        interventions = interventions.filter(priorite=priorite)
    if type_i:
        interventions = interventions.filter(type_intervention=type_i)

    interventions = interventions.order_by('-date_creation')
    paginator = Paginator(interventions, 15)
    page = request.GET.get('page')
    interventions = paginator.get_page(page)

    return render(request, 'core/intervention_list.html', {
        'interventions': interventions,
        'q': q, 'statut': statut, 'priorite': priorite, 'type_i': type_i,
        'can_create': request.user.has_perm('core.add_intervention'),
        'STATUT_CHOICES': Intervention.STATUT_CHOICES,
        'PRIORITE_CHOICES': Intervention.PRIORITE_CHOICES,
        'TYPE_CHOICES': Intervention.TYPE_CHOICES,
    })

@perm_required('core.add_intervention')
def intervention_create(request):
    if request.method == 'POST':
        form = InterventionForm(request.POST)
        if form.is_valid():
            intervention = form.save(commit=False)
            intervention.created_by = request.user
            intervention.save()

            analyse = analyser_description(intervention.description)
            log_activity(request.user, "Création intervention",
                        f"#{intervention.id} — priorité suggérée: {analyse['priorite_suggeree']}")

            if intervention.technicien:
                notifier_assignation(intervention)

            return redirect('intervention_detail', pk=intervention.pk)
        analyse = analyser_description(request.POST.get('description', ''))
    else:
        form = InterventionForm()
        analyse = analyser_description('')

    return render(request, 'core/intervention_form.html', {
        'form': form,
        'title': 'Nouvelle intervention',
        'analyse': analyse,
        'show_scoring': True,
    })

@login_required
def intervention_edit(request, pk):
    intervention = get_object_or_404(Intervention, pk=pk)

    full_edit = request.user.has_perm('core.change_intervention')
    tech = get_technician_profile(request.user)
    is_owner = tech is not None and intervention.technicien_id == tech.id

    if not full_edit and not is_owner:
        return HttpResponseForbidden("Vous ne pouvez modifier que vos interventions.")

    old_tech = intervention.technicien

    if request.method == 'POST':
        if full_edit:
            form = InterventionForm(request.POST, instance=intervention)
        else:
            form = InterventionTechnicianForm(request.POST, instance=intervention)

        old_statut = intervention.statut

        if form.is_valid():
            interv = form.save()
            if old_tech != interv.technicien and interv.technicien:
                notifier_assignation(interv)
            if old_statut != 'terminee' and interv.statut == 'terminee':
                notifier_terminaison(interv)
            log_activity(request.user, "Modification intervention", f"#{interv.id}")
            return redirect('intervention_detail', pk=interv.pk)
    else:
        if full_edit:
            form = InterventionForm(instance=intervention)
        else:
            form = InterventionTechnicianForm(instance=intervention)

    return render(request, 'core/intervention_form.html', {
        'form': form,
        'title': 'Modifier intervention',
        'intervention': intervention,
        'analyse': analyser_description(intervention.description),
    })

@perm_required('core.delete_intervention')
def intervention_delete(request, pk):
    intervention = get_object_or_404(Intervention, pk=pk)
    if request.method == 'POST':
        intervention.delete()
        log_activity(request.user, "Suppression intervention", f"#{pk}")
        return redirect('intervention_list')
    return render(request, 'core/intervention_confirm_delete.html', {'intervention': intervention})

@perm_required('core.change_intervention')
def intervention_assign_technician(request, pk):
    """
    Assigne (ou réassigne) explicitement un technicien à une intervention.
    """
    intervention = get_object_or_404(Intervention, pk=pk)

    if request.method != 'POST':
        return redirect('intervention_detail', pk=intervention.pk)

    form = InterventionAssignForm(request.POST)
    if form.is_valid():
        old_tech = intervention.technicien
        technicien = form.cleaned_data['technicien']
        intervention.technicien = technicien

        update_fields = ['technicien']
        if intervention.statut == 'en_attente':
            intervention.statut = 'planifiee'
            update_fields.append('statut')

        intervention.save(update_fields=update_fields)

        if old_tech != technicien:
            notifier_assignation(intervention)
            if old_tech:
                log_activity(
                    request.user, "Réassignation intervention",
                    f"#{intervention.id} — {old_tech} → {technicien}"
                )
            else:
                log_activity(
                    request.user, "Assignation intervention",
                    f"#{intervention.id} — technicien: {technicien}"
                )
            django_messages.success(request, f"Intervention assignée à {technicien}.")
    else:
        django_messages.error(request, "Veuillez choisir un technicien valide.")

    return redirect('intervention_detail', pk=intervention.pk)


@login_required
def intervention_start(request, pk):
    """Démarrage en un clic par le technicien assigné — passe le statut à 'en_cours'."""
    intervention = get_object_or_404(Intervention, pk=pk)

    if not user_can_edit_intervention(request.user, intervention):
        return HttpResponseForbidden("Vous ne pouvez démarrer que vos interventions.")

    if request.method != 'POST':
        return redirect('intervention_detail', pk=intervention.pk)

    if intervention.statut in ('en_attente', 'planifiee'):
        intervention.statut = 'en_cours'
        intervention.save(update_fields=['statut', 'date_debut'])
        log_activity(request.user, "Démarrage intervention", f"#{intervention.id}")
        django_messages.success(request, "Intervention démarrée.")
    else:
        django_messages.error(
            request,
            f"Impossible de démarrer : l'intervention est déjà « {intervention.get_statut_display()} »."
        )

    return redirect('intervention_detail', pk=intervention.pk)


@login_required
def intervention_finish(request, pk):
    """Fin en un clic par le technicien assigné — passe le statut à 'terminee'."""
    intervention = get_object_or_404(Intervention, pk=pk)

    if not user_can_edit_intervention(request.user, intervention):
        return HttpResponseForbidden("Vous ne pouvez terminer que vos interventions.")

    if request.method != 'POST':
        return redirect('intervention_detail', pk=intervention.pk)

    if intervention.statut == 'en_cours':
        intervention.statut = 'terminee'
        intervention.save(update_fields=['statut', 'date_fin'])
        notifier_terminaison(intervention)
        log_activity(request.user, "Fin intervention", f"#{intervention.id}")
        django_messages.success(request, "Intervention marquée comme terminée.")
    else:
        django_messages.error(
            request,
            "Impossible de terminer : l'intervention doit d'abord être « En cours »."
        )

    return redirect('intervention_detail', pk=intervention.pk)


@login_required
def intervention_scoring(request):
    """Scoring en direct pour le formulaire de création/édition d'intervention."""
    if not (request.user.has_perm('core.add_intervention') or request.user.has_perm('core.change_intervention')):
        return HttpResponseForbidden()

    type_intervention = request.GET.get('type_intervention', 'maintenance')

    def _to_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    intervention_temp = Intervention(
        type_intervention=type_intervention,
        latitude=_to_float(request.GET.get('latitude')),
        longitude=_to_float(request.GET.get('longitude')),
    )

    scores = recommander_technicien(intervention_temp)[:5]
    return JsonResponse({
        'techniciens': [{
            'id': tech.id,
            'nom': f'{tech.prenom} {tech.nom}',
            'specialites': tech.specialites,
            'disponible': tech.disponible,
            'score': score,
        } for tech, score in scores]
    })


@login_required
def intervention_detail(request, pk):
    if is_portal_client(request.user):
        return redirect('client_portal_intervention_detail', pk=pk)

    intervention = get_object_or_404(Intervention, pk=pk)

    if not user_can_access_intervention(request.user, intervention):
        return HttpResponseForbidden()

    tasks = intervention.tasks.all()
    messages_list = intervention.messages.select_related('expediteur').all()
    pieces = intervention.interventionpiece_set.select_related('piece').all()
    incidents = intervention.incidents.select_related('signale_par').all()

    can_assign = request.user.has_perm('core.change_intervention')
    recommandations = []
    assign_form = None
    if can_assign:
        recommandations = recommander_technicien(intervention)[:3]
        assign_form = InterventionAssignForm(initial={'technicien': intervention.technicien_id})

    analyse = analyser_description(intervention.description)

    task_form = TaskForm()
    message_form = MessageForm()
    piece_form = InterventionPieceForm()
    incident_form = IncidentForm()

    return render(request, 'core/intervention_detail.html', {
        'intervention': intervention,
        'tasks': tasks,
        'messages_list': messages_list,
        'pieces': pieces,
        'incidents': incidents,
        'recommandations': recommandations,
        'can_assign': can_assign,
        'assign_form': assign_form,
        'analyse': analyse,
        'task_form': task_form,
        'message_form': message_form,
        'piece_form': piece_form,
        'incident_form': incident_form,
        'can_manage': request.user.has_perm('core.change_intervention'),
        'can_edit': user_can_edit_intervention(request.user, intervention),
    })


# ───────────────────────────────────────────────
# Actions inline sur intervention (tâches, messages, pièces)
# ───────────────────────────────────────────────

def _verifier_acces_intervention(request, intervention):
    if not user_can_edit_intervention(request.user, intervention):
        return HttpResponseForbidden("Vous ne pouvez agir que sur vos interventions.")
    return None


@login_required
def task_create(request, intervention_pk):
    intervention = get_object_or_404(Intervention, pk=intervention_pk)
    denied = _verifier_acces_intervention(request, intervention)
    if denied:
        return denied
    if request.method == 'POST':
        data = request.POST.copy()
        data.setdefault('statut', 'a_faire')
        form = TaskForm(data)
        if form.is_valid():
            task = form.save(commit=False)
            task.intervention = intervention
            task.save()
            log_activity(request.user, "Création tâche", f"Intervention #{intervention_pk}")
        else:
            django_messages.error(request, "Impossible d'ajouter la tâche : " + " ".join(
                f"{f}: {', '.join(errs)}" for f, errs in form.errors.items()
            ))
    return redirect('intervention_detail', pk=intervention_pk)


TASK_STATUT_CYCLE = {'a_faire': 'en_cours', 'en_cours': 'terminee', 'terminee': 'a_faire'}


@login_required
def task_update_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    denied = _verifier_acces_intervention(request, task.intervention)
    if denied:
        return denied
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut and nouveau_statut in dict(Task.STATUT_CHOICES):
            task.statut = nouveau_statut
        else:
            task.statut = TASK_STATUT_CYCLE.get(task.statut, 'a_faire')
        task.save(update_fields=['statut'])
        log_activity(
            request.user, "Modification statut tâche",
            f"Intervention #{task.intervention_id} — {task.titre} → {task.get_statut_display()}"
        )
    return redirect('intervention_detail', pk=task.intervention_id)

@login_required
def message_create(request, intervention_pk):
    intervention = get_object_or_404(Intervention, pk=intervention_pk)
    if not user_can_message_intervention(request.user, intervention):
        return HttpResponseForbidden("Vous n'êtes pas autorisé à écrire sur cette intervention.")
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.intervention = intervention
            msg.expediteur = request.user
            msg.save()
            log_activity(request.user, "Message envoyé", f"Intervention #{intervention_pk}")
        else:
            django_messages.error(request, "Message vide ou invalide.")
    if is_portal_client(request.user):
        return redirect('client_portal_intervention_detail', pk=intervention_pk)
    return redirect('intervention_detail', pk=intervention_pk)

@login_required
def intervention_add_piece(request, intervention_pk):
    intervention = get_object_or_404(Intervention, pk=intervention_pk)
    denied = _verifier_acces_intervention(request, intervention)
    if denied:
        return denied
    if request.method == 'POST':
        form = InterventionPieceForm(request.POST)
        if form.is_valid():
            piece = form.cleaned_data['piece']
            quantite = form.cleaned_data['quantite']
            try:
                with transaction.atomic():
                    StockService.consommer_pour_intervention(intervention, piece, quantite, request.user)
                    ip, created = InterventionPiece.objects.get_or_create(
                        intervention=intervention,
                        piece=piece,
                        defaults={'quantite': quantite}
                    )
                    if not created:
                        ip.quantite = F('quantite') + quantite
                        ip.save(update_fields=['quantite'])
                django_messages.success(request, f"{piece.nom} x{quantite} consommé(e).")
            except ValueError as e:
                django_messages.error(request, str(e))
    return redirect('intervention_detail', pk=intervention_pk)


@login_required
def incident_create(request, intervention_pk):
    intervention = get_object_or_404(Intervention, pk=intervention_pk)
    denied = _verifier_acces_intervention(request, intervention)
    if denied:
        return denied
    if request.method == 'POST':
        form = IncidentForm(request.POST)
        if form.is_valid():
            incident = form.save(commit=False)
            incident.intervention = intervention
            incident.signale_par = request.user
            incident.save()
            log_activity(
                request.user, "Signalement incident",
                f"Intervention #{intervention_pk} — {incident.titre} ({incident.get_gravite_display()})"
            )
            django_messages.success(request, "Incident signalé.")
    return redirect('intervention_detail', pk=intervention_pk)


@login_required
def incident_resolve(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    denied = _verifier_acces_intervention(request, incident.intervention)
    if denied:
        return denied
    if request.method == 'POST':
        incident.resolu = not incident.resolu
        incident.save()
        log_activity(
            request.user,
            "Incident résolu" if incident.resolu else "Incident rouvert",
            f"Intervention #{incident.intervention_id} — {incident.titre}"
        )
    return redirect('intervention_detail', pk=incident.intervention_id)


# ───────────────────────────────────────────────
# Portail client
# ───────────────────────────────────────────────

@login_required
def client_portal_dashboard(request):
    client = get_client_profile(request.user)
    if client is None:
        return HttpResponseForbidden("Votre compte n'est lié à aucune fiche client.")

    interventions = client.interventions.select_related('technicien').order_by('-date_creation')

    context = {
        'client': client,
        'interventions_actives': interventions.filter(statut__in=['en_attente', 'planifiee', 'en_cours']),
        'interventions_terminees': interventions.filter(statut='terminee')[:10],
        'total_interventions': interventions.count(),
    }
    return render(request, 'core/client_portal_dashboard.html', context)


@login_required
def client_portal_intervention_detail(request, pk):
    intervention = get_object_or_404(Intervention, pk=pk)
    client = get_client_profile(request.user)

    if client is None or intervention.client_id != client.id:
        return HttpResponseForbidden("Cette intervention ne concerne pas votre compte.")

    messages_list = intervention.messages.select_related('expediteur').all()
    message_form = MessageForm()

    evaluation_form = None
    if intervention.statut == 'terminee' and not hasattr(intervention, 'evaluation_client'):
        evaluation_form = ClientEvaluationForm()

    return render(request, 'core/client_portal_intervention_detail.html', {
        'intervention': intervention,
        'messages_list': messages_list,
        'message_form': message_form,
        'evaluation_form': evaluation_form,
    })


@login_required
def client_evaluation_create(request, pk):
    """
    Le client note l'intervention (/5) et le technicien (/100) une fois
    l'intervention terminée — une seule fois. Réservé au client concerné.
    """
    intervention = get_object_or_404(Intervention, pk=pk)
    client = get_client_profile(request.user)

    if client is None or intervention.client_id != client.id:
        return HttpResponseForbidden("Cette intervention ne concerne pas votre compte.")
    if intervention.statut != 'terminee':
        django_messages.error(request, "L'intervention doit être terminée avant de pouvoir être évaluée.")
        return redirect('client_portal_intervention_detail', pk=pk)
    if hasattr(intervention, 'evaluation_client'):
        django_messages.error(request, "Cette intervention a déjà été évaluée.")
        return redirect('client_portal_intervention_detail', pk=pk)

    if request.method == 'POST':
        form = ClientEvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.intervention = intervention
            evaluation.save()
            log_activity(request.user, "Évaluation client", f"Intervention #{pk}")
            django_messages.success(request, "Merci pour votre évaluation.")
        else:
            django_messages.error(request, "Merci de vérifier les notes saisies (intervention /5, technicien entre 0 et 100).")
    return redirect('client_portal_intervention_detail', pk=pk)


# ───────────────────────────────────────────────
# Pièces détachées & Stock
# ───────────────────────────────────────────────

@login_required
def sparepart_list(request):
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')
    q = request.GET.get('q', '')
    alertes = request.GET.get('alertes', '')

    parts = SparePart.objects.all()
    if q:
        parts = parts.filter(Q(nom__icontains=q) | Q(reference__icontains=q))
    if alertes:
        parts = parts.filter(quantite_stock__lte=F('quantite_minimale'))

    paginator = Paginator(parts, 20)
    page = request.GET.get('page')
    parts = paginator.get_page(page)

    return render(request, 'core/sparepart_list.html', {
        'parts': parts,
        'q': q,
        'alertes': alertes,
        'can_manage': request.user.has_perm('core.change_sparepart')
    })

@perm_required('core.add_sparepart')
def sparepart_create(request):
    if request.method == 'POST':
        form = SparePartForm(request.POST)
        if form.is_valid():
            part = form.save()
            log_activity(request.user, "Création pièce", part.nom)
            return redirect('sparepart_list')
    else:
        form = SparePartForm()
    return render(request, 'core/sparepart_form.html', {'form': form, 'title': 'Nouvelle pièce'})

@perm_required('core.change_sparepart')
def sparepart_edit(request, pk):
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        form = SparePartForm(request.POST, instance=part)
        if form.is_valid():
            form.save()
            return redirect('sparepart_list')
    else:
        form = SparePartForm(instance=part)
    return render(request, 'core/sparepart_form.html', {'form': form, 'title': 'Modifier pièce'})

@perm_required('core.delete_sparepart')
def sparepart_delete(request, pk):
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        part.delete()
        return redirect('sparepart_list')
    return render(request, 'core/sparepart_confirm_delete.html', {'part': part})

@login_required
def stock_movement_list(request):
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')
    movements = StockMovement.objects.select_related('piece', 'utilisateur').all()
    paginator = Paginator(movements, 25)
    page = request.GET.get('page')
    movements = paginator.get_page(page)
    return render(request, 'core/stock_movement_list.html', {
        'movements': movements,
        'can_manage': request.user.has_perm('core.add_stockmovement')
    })

@perm_required('core.add_stockmovement')
def stock_movement_create(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            piece = form.cleaned_data['piece']
            type_mvt = form.cleaned_data['type_mouvement']
            quantite = form.cleaned_data['quantite']
            raison = form.cleaned_data['raison']
            try:
                StockService.adjust(piece, type_mvt, quantite, raison, request.user)
                django_messages.success(request, "Mouvement enregistré.")
                return redirect('stock_movement_list')
            except ValueError as e:
                django_messages.error(request, str(e))
    else:
        form = StockMovementForm()
    return render(request, 'core/stock_movement_form.html', {'form': form})


# ───────────────────────────────────────────────
# Rapports
# ───────────────────────────────────────────────

@login_required
def report_list(request):
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')

    reports = Report.objects.select_related('intervention__client', 'intervention__technicien').all()
    if not has_global_intervention_access(request.user):
        tech = get_technician_profile(request.user)
        reports = reports.filter(intervention__technicien=tech) if tech else Report.objects.none()

    paginator = Paginator(reports, 20)
    page = request.GET.get('page')
    reports = paginator.get_page(page)
    return render(request, 'core/report_list.html', {'reports': reports})

@login_required
def report_detail(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if not user_can_access_intervention(request.user, report.intervention):
        return HttpResponseForbidden()
    return render(request, 'core/report_detail.html', {'report': report})

@login_required
def report_create(request, intervention_pk):
    intervention = get_object_or_404(Intervention, pk=intervention_pk)

    if not user_can_access_intervention(request.user, intervention):
        return HttpResponseForbidden()
    if not request.user.has_perm('core.add_report'):
        return HttpResponseForbidden("Votre rôle ne permet pas de rédiger de rapport.")

    if hasattr(intervention, 'report'):
        return redirect('report_edit', pk=intervention.report.pk)

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.intervention = intervention
            report.save()
            report.generer_complet()

            # NOTE : pas de notifier_terminaison() ici. Cette notification est
            # envoyée une seule fois, au moment où l'intervention PASSE à
            # 'terminee' (voir intervention_finish / intervention_edit). Le
            # rapport est généralement rédigé après coup, une fois
            # l'intervention déjà terminée — la renvoyer ici dupliquait
            # l'email au créateur à chaque rédaction de rapport.

            log_activity(request.user, "Création rapport", f"Intervention #{intervention_pk}")
            return redirect('report_detail', pk=report.pk)
    else:
        form = ReportForm()

    return render(request, 'core/report_form.html', {
        'form': form,
        'intervention': intervention,
        'title': 'Nouveau rapport'
    })

@login_required
def report_edit(request, pk):
    report = get_object_or_404(Report, pk=pk)

    if not user_can_access_intervention(request.user, report.intervention):
        return HttpResponseForbidden()
    if not request.user.has_perm('core.change_report'):
        return HttpResponseForbidden("Votre rôle ne permet pas de modifier de rapport.")

    if request.method == 'POST':
        form = ReportForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            report.generer_complet()
            return redirect('report_detail', pk=report.pk)
    else:
        form = ReportForm(instance=report)
    return render(request, 'core/report_form.html', {
        'form': form,
        'intervention': report.intervention,
        'title': 'Modifier rapport'
    })

@login_required
def report_pdf(request, pk):
    report = get_object_or_404(Report, pk=pk)

    if not user_can_access_intervention(request.user, report.intervention):
        return HttpResponseForbidden()

    if not XHTML2PDF_AVAILABLE:
        return HttpResponse(
            '<h1>Module xhtml2pdf non installé</h1>'
            '<p>Pour activer les PDF, installez : <code>pip install xhtml2pdf</code></p>'
            '<p><a href="/rapports/{}/">← Retour au rapport</a></p>'.format(pk),
            status=503
        )
    template_path = 'core/report_pdf.html'
    context = {'report': report}
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_{report.intervention.id}.pdf"'
    html = render(request, template_path, context).content.decode('utf-8')
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Erreur génération PDF', status=500)
    return response


# ───────────────────────────────────────────────
# Statistiques
# ───────────────────────────────────────────────

@perm_required('core.view_statistics')
def statistics(request):
    terminees = Intervention.objects.filter(statut='terminee')
    durees = [i.duree_reelle() for i in terminees if i.duree_reelle()]
    duree_moyenne = sum(durees) / len(durees) if durees else 0

    repartition_type = Intervention.objects.values('type_intervention').annotate(
        count=Count('id')
    ).order_by('-count')

    repartition_statut = Intervention.objects.values('statut').annotate(
        count=Count('id')
    )

    pic_jour = Intervention.objects.annotate(
        jour=TruncDate('date_creation')
    ).values('jour').annotate(count=Count('id')).order_by('-count')[:7]

    satisfaction = Report.objects.exclude(satisfaction_client__isnull=True).aggregate(
        avg=Avg('satisfaction_client')
    )['avg'] or 0

    stock_value = sum(p.valeur_stock() for p in SparePart.objects.all())

    alertes_stock = SparePart.objects.filter(
        quantite_stock__lte=F('quantite_minimale')
    )

    context = {
        'total_interventions': Intervention.objects.count(),
        'interventions_terminees': terminees.count(),
        'duree_moyenne': round(duree_moyenne, 1),
        'repartition_type': repartition_type,
        'repartition_statut': repartition_statut,
        'pic_jour': pic_jour,
        'satisfaction_moyenne': round(satisfaction, 1),
        'stock_value': stock_value,
        'alertes_stock': alertes_stock,
    }
    return render(request, 'core/statistics.html', context)


# ───────────────────────────────────────────────
# Recherche globale
# ───────────────────────────────────────────────

@login_required
def search(request):
    if is_portal_client(request.user):
        return redirect('client_portal_dashboard')
    q = request.GET.get('q', '')
    if len(q) < 2:
        return render(request, 'core/search_results.html', {'q': q, 'too_short': True})

    clients = Client.objects.filter(
        Q(nom__icontains=q) | Q(email__icontains=q) | Q(secteur__icontains=q)
    )[:10]

    technicians = Technician.objects.filter(
        Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(specialites__icontains=q)
    )[:10]

    interventions = Intervention.objects.filter(
        Q(titre__icontains=q) | Q(description__icontains=q) |
        Q(client__nom__icontains=q)
    )[:10]

    pieces = SparePart.objects.filter(
        Q(nom__icontains=q) | Q(reference__icontains=q)
    )[:10]

    return render(request, 'core/search_results.html', {
        'q': q,
        'clients': clients,
        'technicians': technicians,
        'interventions': interventions,
        'pieces': pieces,
    })


# ───────────────────────────────────────────────
# Journal d'activité
# ───────────────────────────────────────────────

@perm_required('core.view_activitylog')
def activity_log(request):
    logs = ActivityLog.objects.select_related('utilisateur').all()[:100]
    return render(request, 'core/activity_log.html', {'logs': logs})


# ───────────────────────────────────────────────
# Exports CSV
# ───────────────────────────────────────────────

@perm_required('core.export_interventions')
def export_interventions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="interventions.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Titre', 'Client', 'Technicien', 'Type', 'Priorite', 'Statut', 'Date creation'])
    for i in Intervention.objects.select_related('client', 'technicien').all():
        writer.writerow([
            i.id, i.titre, i.client.nom if i.client else '',
            str(i.technicien) if i.technicien else '',
            i.get_type_intervention_display(), i.get_priorite_display(),
            i.get_statut_display(), i.date_creation.strftime('%d/%m/%Y %H:%M')
        ])
    return response

@perm_required('core.export_stock')
def export_stock_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stock.csv"'
    writer = csv.writer(response)
    writer.writerow(['Reference', 'Nom', 'Quantite', 'Minimale', 'Prix unitaire', 'Fournisseur'])
    for p in SparePart.objects.all():
        writer.writerow([p.reference, p.nom, p.quantite_stock, p.quantite_minimale, p.prix_unitaire, p.fournisseur])
    return response


@login_required
def recherche_globale(request):
    """Recherche globale pour la barre du top bar."""
    data = {'interventions': [], 'clients': [], 'techniciens': [], 'pieces': []}

    if is_portal_client(request.user):
        return JsonResponse(data)

    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse(data)

    interventions_qs = Intervention.objects.all()
    if not has_global_intervention_access(request.user):
        tech = get_technician_profile(request.user)
        interventions_qs = interventions_qs.filter(technicien=tech) if tech else Intervention.objects.none()

    interventions = interventions_qs.filter(
        Q(titre__icontains=q) | Q(client__nom__icontains=q)
    ).select_related('client')[:5]
    data['interventions'] = [{
        'titre': i.titre,
        'client': i.client.nom if i.client else '',
        'statut': i.get_statut_display(),
        'url': reverse('intervention_detail', args=[i.pk]),
    } for i in interventions]

    clients = Client.objects.filter(nom__icontains=q)[:5]
    data['clients'] = [{
        'nom': c.nom,
        'url': reverse('client_list') + '?' + urlencode({'q': c.nom}),
    } for c in clients]

    techniciens = Technician.objects.annotate(
        nom_complet=Concat('prenom', Value(' '), 'nom')
    ).filter(
        Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(nom_complet__icontains=q)
    )[:5]
    data['techniciens'] = [{
        'nom': f'{t.prenom} {t.nom}',
        'url': reverse('technician_list') + '?' + urlencode({'q': t.nom}),
    } for t in techniciens]

    pieces = SparePart.objects.filter(
        Q(nom__icontains=q) | Q(reference__icontains=q)
    )[:5]
    data['pieces'] = [{
        'nom': p.nom,
        'reference': p.reference,
        'url': reverse('sparepart_list') + '?' + urlencode({'q': p.nom}),
    } for p in pieces]

    return JsonResponse(data)