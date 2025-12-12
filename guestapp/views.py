from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.

def guesthome(request):
    return render(request, 'guest/index.html')

def ngo_reg(request):
    if request.method == 'POST':
        # Process NGO registration here
        # Add database save logic later
        pass
    return render(request, 'guest/ngo_reg.html')

def ngo_vol_sel(request):
    return render(request, 'guest/ngo_vol_sel.html')

def login(request):
    return render(request, 'guest/login.html')