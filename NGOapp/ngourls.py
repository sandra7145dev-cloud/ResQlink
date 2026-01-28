from django.urls import path
from . import views

urlpatterns = [
    path('ngohome/', views.ngo_dashboard, name='ngohome'),
    path('accept-reject/', views.ngo_accept_reject_request, name='ngo_accept_reject_request'),
    path('accepted_tasks/', views.ngo_accepted_tasks, name='ngo_accepted_tasks'),
    path('complete_task/<int:aid>/', views.ngo_complete_task, name='ngo_complete_task'),
    path('completed_tasks/', views.ngo_completed_history, name='ngo_completed_tasks'),
    # path('get-subcategories/', views.get_subcategories, name='get_subcategories'),
    # path('submit-help-details/', views.submit_help_details, name='submit_help_details'),
    # path('accept-reject/', views.ngo_accept_reject_request, name='ngo_accept_reject_request'),
]