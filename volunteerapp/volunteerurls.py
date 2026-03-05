from django.urls import path
from . import views
urlpatterns = [
    path('volunteer_dashboard/', views.volunteer_dashboard, name='volunteer_dashboard'),
    path('profile/', views.volunteer_profile, name='volunteer_profile'),
    path('logout/', views.volunteer_logout, name='volunteer_logout'),
    path('update_work_status/<int:aid>/', views.update_work_status, name='update_work_status'),
]