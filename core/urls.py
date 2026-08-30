from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('', views.dashboard, name='dashboard'),
    # Suivi en temps réel
    path('suivi/', views.suivi_temps_reel, name='suivi_temps_reel'),
    path('suivi/data/', views.suivi_temps_reel_data, name='suivi_temps_reel_data'),

    # Clients
    path('clients/', views.client_list, name='client_list'),
    path('clients/nouveau/', views.client_create, name='client_create'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('clients/<int:pk>/modifier/', views.client_edit, name='client_edit'),
    path('clients/<int:pk>/supprimer/', views.client_delete, name='client_delete'),

    # Techniciens
    path('techniciens/', views.technician_list, name='technician_list'),
    path('techniciens/nouveau/', views.technician_create, name='technician_create'),
    path('techniciens/<int:pk>/', views.technician_detail, name='technician_detail'),
    path('techniciens/<int:pk>/modifier/', views.technician_edit, name='technician_edit'),
    path('techniciens/<int:pk>/supprimer/', views.technician_delete, name='technician_delete'),

    # Interventions
    path('interventions/', views.intervention_list, name='intervention_list'),
    path('interventions/nouvelle/', views.intervention_create, name='intervention_create'),
    path('interventions/<int:pk>/', views.intervention_detail, name='intervention_detail'),
    path('interventions/<int:pk>/modifier/', views.intervention_edit, name='intervention_edit'),
    path('interventions/<int:pk>/supprimer/', views.intervention_delete, name='intervention_delete'),
    path('interventions/<int:pk>/assigner/', views.intervention_assign_technician, name='intervention_assign_technician'),
    path('interventions/<int:pk>/demarrer/', views.intervention_start, name='intervention_start'),
    path('interventions/<int:pk>/terminer/', views.intervention_finish, name='intervention_finish'),
    path('interventions/scoring/', views.intervention_scoring, name='intervention_scoring'),

    # Actions inline
    path('interventions/<int:intervention_pk>/taches/creer/', views.task_create, name='task_create'),
    path('taches/<int:pk>/statut/', views.task_update_status, name='task_update_status'),
    path('interventions/<int:intervention_pk>/messages/creer/', views.message_create, name='message_create'),
    path('interventions/<int:intervention_pk>/pieces/ajouter/', views.intervention_add_piece, name='intervention_add_piece'),
    path('interventions/<int:intervention_pk>/incidents/signaler/', views.incident_create, name='incident_create'),
    path('incidents/<int:pk>/resoudre/', views.incident_resolve, name='incident_resolve'),

    # Portail client
    path('portail/', views.client_portal_dashboard, name='client_portal_dashboard'),
    path('portail/interventions/<int:pk>/', views.client_portal_intervention_detail, name='client_portal_intervention_detail'),
    path('portail/interventions/<int:pk>/evaluer/', views.client_evaluation_create, name='client_evaluation_create'),

    # Stock
    path('stock/', views.sparepart_list, name='sparepart_list'),
    path('stock/nouveau/', views.sparepart_create, name='sparepart_create'),
    path('stock/<int:pk>/modifier/', views.sparepart_edit, name='sparepart_edit'),
    path('stock/<int:pk>/supprimer/', views.sparepart_delete, name='sparepart_delete'),
    path('stock/mouvements/', views.stock_movement_list, name='stock_movement_list'),
    path('stock/mouvements/nouveau/', views.stock_movement_create, name='stock_movement_create'),

    # Rapports
    path('rapports/', views.report_list, name='report_list'),
    path('rapports/<int:pk>/', views.report_detail, name='report_detail'),
    path('interventions/<int:intervention_pk>/rapport/creer/', views.report_create, name='report_create'),
    path('rapports/<int:pk>/modifier/', views.report_edit, name='report_edit'),
    path('rapports/<int:pk>/pdf/', views.report_pdf, name='report_pdf'),

    # Statistiques & recherche
    path('statistiques/', views.statistics, name='statistics'),
    path('recherche/', views.search, name='search'),
    path('activite/', views.activity_log, name='activity_log'),

    # Exports
    path('export/interventions/', views.export_interventions_csv, name='export_interventions'),
    path('export/stock/', views.export_stock_csv, name='export_stock'),
    path('recherche/ajax/', views.recherche_globale, name='recherche_globale'),
]