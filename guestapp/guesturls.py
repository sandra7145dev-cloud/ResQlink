from django.urls import path
from . import views

urlpatterns = [
    path('guesthome/', views.guesthome, name='guesthome'),
    path('ngo_reg/', views.ngo_reg, name='ngo_reg'),
    path('login/', views.login, name='login'),
    path('ngo_vol_sel/', views.ngo_vol_sel, name='ngo_vol_sel'),
    path('volunteer_reg/', views.volunteer_reg, name='volunteer_reg'),
]