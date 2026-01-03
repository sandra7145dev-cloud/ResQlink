from django.shortcuts import render, redirect
from django.http import HttpResponse
# Create your views here.
def volunteerhome(request):
    return render(request, 'volunteer/index.html')