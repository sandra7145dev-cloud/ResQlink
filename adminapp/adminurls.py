from django.urls import path
from . import views

urlpatterns = [
    path('adminhome/', views.adminhome, name='adminhome'),
    path('taluk_reg/', views.taluk_reg, name='talukreg'),
    path('viewtaluk/', views.viewtaluk, name='viewtaluk'),
    path('edittaluk/<int:tid>/', views.edittaluk, name='edittaluk'),
    path('deletetaluk/<int:tid>/', views.deletetaluk, name='deletetaluk'),
    path('ward_reg/', views.ward_reg, name='wardreg'),
    path('category_reg/',views.category_reg, name='catreg'),
    path('viewcategory/',views.viewcategory, name='viewcategory'),
    path('editcategory/<int:cid>/',views.editcategory, name='editcategory'),
    path('deletecategory/<int:cid>/',views.deletecategory,name='deletecategory'),
    path('subcategory_reg/',views.subcategory_reg, name='subcatreg'),
]