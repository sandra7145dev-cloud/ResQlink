from django.urls import path
from . import views

urlpatterns = [
    path('ngohome/', views.ngohome, name='ngohome'),
    path('get-subcategories/', views.get_subcategories, name='get_subcategories'),
    path('submit-help-details/', views.submit_help_details, name='submit_help_details'),
]