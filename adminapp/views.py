from django.shortcuts import render
from django.http import HttpResponse
from .models import tbl_location
from .models import tbl_panchayat
# Create your views here.
def adminhome(request):
    return render(request, 'admin/index.html')

#Panchayat registration
def panchayat_reg(request):
    if request.method == 'POST':
        panname = request.POST.get('panname')
        pan_obj = tbl_panchayat()
        pan_obj.PanchayatName = panname
        pan_obj.save()
    return render(request, 'admin/panchayat_reg.html')

def viewpanchayat(request):
    panchayats = tbl_panchayat.objects.all()
    return render(request, 'admin/viewpanchayat.html', {'panchayats': panchayats})

def editpanchayat(request, pid):
    panchayat = tbl_panchayat.objects.get(PanchayatID=pid)
    if request.method == 'POST':
        panname = request.POST.get('panname')
        panchayat.PanchayatName = panname
        panchayat.save()
        panchayats = tbl_panchayat.objects.all()
        return render(request, 'admin/viewpanchayat.html', {'panchayats': panchayats})
    else:
        panchayat = tbl_panchayat.objects.get(PanchayatID=pid)
        return render(request, 'admin/editpanchayat.html', {'panchayat': panchayat})
    
def deletepanchayat(request, pid):
    panchayat = tbl_panchayat.objects.get(PanchayatID=pid)
    panchayat.delete()
    return viewpanchayat(request)
    
def location_reg(request):
    return render(request, 'admin/location_reg.html')

def locreg(request):
    if request.method == 'POST':
        locname = request.POST.get('locname')
        loc_obj = tbl_location()
        loc_obj.LocationName = locname
        loc_obj.save()
        return render(request, 'admin/location_reg.html')
    
def viewlocation(request):
    locations = tbl_location.objects.all()
    return render(request, 'admin/viewlocation.html', {'locations': locations})

def editlocation(request, lid):
    location = tbl_location.objects.get(LocationID=lid)
    if request.method == 'POST':
        locname = request.POST.get('locname')
        location.LocationName = locname
        location.save()
        return viewlocation(request)
    else:
        location = tbl_location.objects.get(LocationID=lid)
        return render(request, 'admin/editlocation.html', {'location': location})
        
def deletelocation(request, lid):
    location = tbl_location.objects.get(LocationID=lid)
    location.delete()
    return viewlocation(request)