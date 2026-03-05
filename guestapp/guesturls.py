from django.urls import path
from . import views

urlpatterns = [
    path('', views.guesthome, name='guesthome'),
    path('ngo_reg/', views.ngo_reg, name='ngo_reg'),
    path('login/', views.login, name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('ngo_vol_sel/', views.ngo_vol_sel, name='ngo_vol_sel'),
    path('volunteer_reg/', views.volunteer_reg, name='volunteer_reg'),
    path('helprequest/' ,views.helpreq, name="helpreq"),
    path('api/localbodies/<int:taluk_id>/', views.get_localbodies_by_taluk, name='get_localbodies_by_taluk'),
    path('api/wards/<int:localbody_id>/', views.get_wards_by_localbody, name='get_wards_by_localbody'),
]