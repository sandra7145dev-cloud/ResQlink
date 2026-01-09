from django.urls import path
from . import views

urlpatterns = [
    path('adminhome/', views.adminhome, name='adminhome'),
    path('taluk_reg/', views.taluk_reg, name='talukreg'),
    path('viewtaluk/', views.viewtaluk, name='viewtaluk'),
    path('edittaluk/<int:tid>/', views.edittaluk, name='edittaluk'),
    path('deletetaluk/<int:tid>/', views.deletetaluk, name='deletetaluk'),

    path('localbodytype_reg/', views.localbodytype, name='localbodytypereg'),
    path('viewlocalbodytype/', views.viewlocalbodytype, name='viewlocalbodytype'),
    path('editlocalbodytype/<int:id>/', views.editlocalbodytype, name='editlocalbodytype'),
    path('deletelocalbodytype/<int:id>/', views.deletelocalbodytype, name='deletelocalbodytype'),

    path('localbody_reg/', views.localbody, name='localbody'),
    path('viewlocalbody/', views.viewlocalbody, name='viewlocalbody'),
    path('filter_localbody/', views.filter_localbody, name='filter_localbody'),
    path('editlocalbody/<int:id>/', views.editlocalbody, name='editlocalbody'),
    path('deletelocalbody/<int:id>/', views.deletelocalbody, name='deletelocalbody'),

    path('ward_reg/', views.ward_reg, name='wardreg'),
    path('viewward/', views.viewward, name='viewward'),
    path('filter_ward/', views.filter_ward, name='filter_ward'),
    path('localbodies_by_taluk/', views.localbodies_by_taluk, name='localbodies_by_taluk'),
    path('editward/<int:wid>/', views.editward, name='editward'),
    path('deleteward/<int:wid>/', views.deleteward, name='deleteward'),

    path('category_reg/',views.category_reg, name='catreg'),
    path('viewcategory/',views.viewcategory, name='viewcategory'),
    path('editcategory/<int:cid>/',views.editcategory, name='editcategory'),
    path('deletecategory/<int:cid>/',views.deletecategory,name='deletecategory'),
    path('subcategory_reg/',views.subcategory_reg, name='subcatreg'),
    path('viewsubcategory/',views.viewsubcategory, name='viewsubcategory'),
    path('filter_subcategory/',views.filter_subcategory, name='filter_subcategory'),
    path('editsubcategory/<int:sid>/',views.editsubcategory, name='editsubcategory'),
    path('deletesubcategory/<int:sid>/',views.deletesubcategory,name='deletesubcategory'),
    path('disaster_reg/',views.disaster_reg, name='disasterreg'),
    path('viewdisaster/',views.viewdisaster, name='viewdisaster'),
    path('editdisaster/<int:did>/',views.editdisaster, name='editdisaster'),
    path('deletedisaster/<int:did>/',views.deletedisaster, name='deletedisaster'),
    path('service_reg/',views.service_reg, name='servicereg'),
    path('viewservice/',views.viewservice, name='viewservice'),
    path('editservice/<int:sid>/',views.editservice, name='editservice'),
    path('deleteservice/<int:sid>/',views.deleteservice, name='deleteservice'),

    path('viewngo/', views.viewngo, name='viewngo'),
    path('approve_ngo/<int:ngoid>/', views.approve_ngo, name='approve_ngo'),
    path('reject_ngo/<int:ngoid>/', views.reject_ngo, name='reject_ngo'),

    path('viewvolunteer/', views.viewvolunteer, name='viewvolunteer'),
    path('approve_vol/<int:volid>/', views.approve_vol, name='approve_volunteer'),
    path('reject_vol/<int:volid>/', views.reject_vol, name='reject_volunteer'),   
]