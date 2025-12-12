from django.shortcuts import render
from django.http import HttpResponse
from .models import tbl_subcategory, tbl_category,tbl_taluk,tbl_localbody_type

# Create your views here.
def adminhome(request):
    return render(request, 'admin/index.html')

#Taluk registration
def taluk_reg(request):
    if request.method == 'POST':
        talukname = request.POST.get('talukname')
        taluk_obj = tbl_taluk()
        taluk_obj.TalukName = talukname
        taluk_obj.save()
    return render(request, 'admin/taluk_reg.html')


def viewtaluk(request):
    taluks = tbl_taluk.objects.all()
    return render(request, 'admin/viewtaluk.html', {'taluks': taluks})

def edittaluk(request, tid):
    taluk = tbl_taluk.objects.get(TalukID=tid)
    if request.method == 'POST':
        talukname = request.POST.get('talukname')
        taluk.TalukName = talukname
        taluk.save()
        taluks = tbl_taluk.objects.all()
        return render(request, 'admin/viewtaluk.html', {'taluks': taluks})
    else:
        taluk = tbl_taluk.objects.get(TalukID=tid)
        return render(request, 'admin/edittaluk.html', {'taluk': taluk})
    
def deletetaluk(request, tid):
    taluk = tbl_taluk.objects.get(TalukID=tid)
    taluk.delete()
    return viewtaluk(request)

def localbodytype(request):
    if request.method == 'POST':
        localbodytypename = request.POST.get('localbodytypename')
        localbodytype_obj = tbl_localbody_type()
        localbodytype_obj.TypeName = localbodytypename
        localbodytype_obj.save()
    return render(request, 'admin/localbodytype_reg.html')
    
def viewlocalbodytype(request):
    localbodytypes = tbl_localbody_type.objects.all()
    return render(request, 'admin/localbodytypeview.html', {'localbodytypes': localbodytypes})

def editlocalbodytype(request, id):
    localbodytype= tbl_localbody_type.objects.get(TypeID=id)
    if request.method == 'POST':
        localbodytypename = request.POST.get('localbodytypename')
        localbodytype.TypeName = localbodytypename
        localbodytype.save()
        localbodytypes = tbl_localbody_type.objects.all()
        return render(request, 'admin/localbodytypeview.html', {'localbodytypes': localbodytypes})
    else:
        localbodytype= tbl_localbody_type.objects.get(TypeID=id)
        return render(request, 'admin/editlocalbodytype.html', {'localbodytype': localbodytype})

def deletelocalbodytype(request, id):
    localbodytype = tbl_localbody_type.objects.get(TypeID=id)
    localbodytype.delete()
    return viewlocalbodytype(request)

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

def viewcategory(request):
    categories = tbl_category.objects.all()
    return render(request, 'admin/viewcategory.html', {'categories': categories})

def editcategory(request, cid):
    category = tbl_category.objects.get(CategoryID=cid)
    if request.method == 'POST':
        catname = request.POST.get('catname')
        category.CategoryName = catname
        category.save()
        categories = tbl_category.objects.all()
        return render(request, 'admin/viewcategory.html', {'categories': categories})
    else:
        category = tbl_category.objects.get(CategoryID=cid)
        return render(request, 'admin/editcategory.html', {'category': category})
    
def deletecategory(request, cid):
    category = tbl_category.objects.get(CategoryID=cid)
    category.delete()
    return viewcategory(request)

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