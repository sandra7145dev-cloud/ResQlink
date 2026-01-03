from django.urls import path
from . import views
urlpatterns = [
    path('volunteerhome/', views.volunteerhome, name='volunteerhome'),
]