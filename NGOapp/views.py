from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.

def ngohome(request):
    return render(request, 'ngo/index.html')

# Create your views here.
