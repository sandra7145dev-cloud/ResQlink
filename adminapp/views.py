from django.shortcuts import render
from django.http import HttpResponse
from .models import tbl_subcategory, tbl_ward, tbl_panchayat, tbl_category

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
    
def ward_reg(request):
    panchayats = tbl_panchayat.objects.all()
    if request.method == 'POST':
        wardname = request.POST.get('wardname')
        panchayatid = request.POST.get('panchayatid')
        ward_obj = tbl_ward()
        ward_obj.WardName = wardname
        ward_obj.panchayatID = tbl_panchayat.objects.get(PanchayatID=panchayatid)
        ward_obj.save()
    return render(request, 'admin/ward_reg.html', {'panchayats': panchayats})

def category_reg(request):
    if request.method == 'POST':
        catname = request.POST.get('catname')
        cat_obj = tbl_category()
        cat_obj.CategoryName = catname
        cat_obj.save()
    return render(request, 'admin/category_reg.html')

def subcategory_reg(request):
    categories = tbl_category.objects.all()
    if request.method == 'POST':
        subcatname = request.POST.get('subcatname')
        categoryid = request.POST.get('categoryid')
        subcat_obj = tbl_subcategory()
        subcat_obj.SubCategoryname = subcatname
        subcat_obj.categoryID = tbl_category.objects.get(CategoryID=categoryid)
        subcat_obj.save()
    return render(request, 'admin/subcategory_reg.html', {'categories': categories})