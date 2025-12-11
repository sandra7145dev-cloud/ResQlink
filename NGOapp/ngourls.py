from django.urls import path
from . import views

urlpatterns = [
    path('ngohome/', views.ngohome, name='ngohome'),
]