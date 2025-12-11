from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.

def guesthome(request):
    return render(request, 'guest/index.html')

def login(request):
    return render(request, 'guest/login.html')