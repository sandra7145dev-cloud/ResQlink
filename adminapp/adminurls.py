from django.urls import path
from . import views

urlpatterns = [
    path('adminhome/', views.adminhome, name='adminhome'),
    path('panchayat_reg/', views.panchayat_reg, name='panreg'),
    path('viewpanchayat/', views.viewpanchayat, name='viewpanchayat'),
    path('editpanchayat/<int:pid>/', views.editpanchayat, name='editpanchayat'),
    path('deletepanchayat/<int:pid>/', views.deletepanchayat, name='deletepanchayat'),
    path('ward_reg/', views.ward_reg, name='wardreg'),
    path('category_reg/',views.category_reg, name='catreg'),
    path('subcategory_reg/',views.subcategory_reg, name='subcatreg'),
]