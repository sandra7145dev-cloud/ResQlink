from django.urls import path
from . import views

urlpatterns = [
    path('adminhome/', views.adminhome, name='adminhome'),
    path('panchayat_reg/', views.panchayat_reg, name='panreg'),
    path('viewpanchayat/', views.viewpanchayat, name='viewpanchayat'),
    path('editpanchayat/<int:pid>/', views.editpanchayat, name='editpanchayat'),
    path('deletepanchayat/<int:pid>/', views.deletepanchayat, name='deletepanchayat'),
    path('location_reg/', views.location_reg, name='location_reg'),
    path('locreg/', views.locreg, name='locreg'),
    path('viewlocation/', views.viewlocation, name='viewlocation'),
    path('editlocation/<int:lid>/', views.editlocation, name='editlocation'),
    path('deletelocation/<int:lid>/', views.deletelocation, name='deletelocation'),
]