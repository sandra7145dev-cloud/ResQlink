from django.urls import path
from . import views

urlpatterns = [
    path('guesthome/', views.guesthome, name='guesthome'),
    path('login/', views.login, name='login'),
]