from django.urls import path
from . import views
urlpatterns = [
    path('volunteer_dashboard/', views.volunteer_dashboard, name='volunteer_dashboard'),
    path('update_work_status/<int:assignment_id>/', views.update_work_status, name='update_work_status'),
]