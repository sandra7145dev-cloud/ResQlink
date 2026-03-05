from django.urls import path
from . import views

urlpatterns = [
    path('ngohome/', views.ngo_dashboard, name='ngohome'),
    path('profile/', views.ngo_profile, name='ngo_profile'),
    path('logout/', views.ngo_logout, name='ngo_logout'),
    path('accept-reject/', views.ngo_accept_reject_request, name='ngo_accept_reject_request'),
    path('accepted_tasks/', views.ngo_accepted_tasks, name='ngo_accepted_tasks'),
    path('assign_waiting_volunteer/<int:aid>/', views.ngo_assign_waiting_volunteer, name='ngo_assign_waiting_volunteer'),
    path('complete_task/<int:aid>/', views.ngo_complete_task, name='ngo_complete_task'),
    path('completed_tasks/', views.ngo_completed_history, name='ngo_completed_tasks'),
    path('ngo_add_items/', views.ngo_help_page, name='ngo_add_items'),
    path('submit-help-details/', views.submit_help_details, name='submit_help_details'),
    path('get-subcategories/', views.get_subcategories, name='get_subcategories'),
    path('api/community/<int:camp_id>/', views.get_community_details, name='get_community_details'),
    # path('get-subcategories/', views.get_subcategories, name='get_subcategories'),
    # path('submit-help-details/', views.submit_help_details, name='submit_help_details'),
    # path('accept-reject/', views.ngo_accept_reject_request, name='ngo_accept_reject_request'),
]