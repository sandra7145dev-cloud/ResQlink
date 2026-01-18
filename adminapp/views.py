from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.contrib import messages

from guestapp.models import tbl_login, tbl_ngo_reg, tbl_volunteer_reg
from .models import tbl_subcategory, tbl_category, tbl_taluk, tbl_localbody_type, tbl_localbody,  tbl_ward , tbl_disaster, tbl_service_type
from django.views.decorators.http import require_http_methods

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

def localbody(request):
    taluks = tbl_taluk.objects.all()
    localbodies = tbl_localbody_type.objects.all()
    if request.method == 'POST':
        localbodyname = request.POST.get('localbodyname')
        localbodyid = request.POST.get('localbodyid')
        localbody_obj = tbl_localbody()
        localbody_obj.LocalbodyName = localbodyname
        localbody_obj.TypeID = tbl_localbody_type.objects.get(TypeID=localbodyid)
        localbody_obj.TalukId = tbl_taluk.objects.get(TalukID=request.POST.get('talukid'))
        localbody_obj.save()
    return render(request, 'admin/localbody_reg.html', {'taluks': taluks, 'localbodies': localbodies})

def ward_reg(request):
    taluks = tbl_taluk.objects.all()
    localbodies = tbl_localbody.objects.none()  # filled via JS after taluk select
    if request.method == 'POST':
        ward_number = request.POST.get('wardnumber')
        localbody_id = request.POST.get('localbodyid')
        ward_obj = tbl_ward()
        ward_obj.WardNumber = ward_number
        ward_obj.LocalbodyID = tbl_localbody.objects.get(LocalbodyID=localbody_id)
        ward_obj.save()
    return render(request, 'admin/ward_reg.html', {
        'taluks': taluks,
        'localbodies': localbodies
    })


def viewward(request):
    taluks = tbl_taluk.objects.all()
    wards = tbl_ward.objects.select_related('LocalbodyID', 'LocalbodyID__TalukId')
    return render(request, 'admin/ward_view.html', {
        'taluks': taluks,
        'wards': wards,
        'localbodies': tbl_localbody.objects.none(),  # populated via JS when taluk is chosen
    })


@require_http_methods(["GET"])
def filter_ward(request):
    taluk_id = request.GET.get('taluk_id', '')
    localbody_id = request.GET.get('localbody_id', '')

    wards = tbl_ward.objects.select_related('LocalbodyID', 'LocalbodyID__TalukId')

    if taluk_id:
        wards = wards.filter(LocalbodyID__TalukId=taluk_id)
    if localbody_id:
        wards = wards.filter(LocalbodyID=localbody_id)

    data = [
        {
            'WardID': w.WardID,
            'WardNumber': w.WardNumber,
            'LocalbodyID': w.LocalbodyID.LocalbodyID,
            'LocalbodyName': w.LocalbodyID.LocalbodyName,
            'TalukName': w.LocalbodyID.TalukId.TalukName,
        }
        for w in wards
    ]

    return JsonResponse(data, safe=False)


@require_http_methods(["GET"])
def localbodies_by_taluk(request):
    taluk_id = request.GET.get('taluk_id')
    if not taluk_id:
        return JsonResponse([], safe=False)

    localbodies = tbl_localbody.objects.filter(TalukId=taluk_id)
    data = [
        {
            'LocalbodyID': lb.LocalbodyID,
            'LocalbodyName': lb.LocalbodyName,
        }
        for lb in localbodies
    ]
    return JsonResponse(data, safe=False)

def editward(request, wid):
    taluks = tbl_taluk.objects.all()
    ward = tbl_ward.objects.select_related('LocalbodyID', 'LocalbodyID__TalukId').get(WardID=wid)

    if request.method == 'POST':
        ward_number = request.POST.get('wardnumber')
        localbody_id = request.POST.get('localbodyid')

        ward.WardNumber = ward_number
        ward.LocalbodyID = tbl_localbody.objects.get(LocalbodyID=localbody_id)
        ward.save()
        return redirect('viewward')

    # GET: preload localbodies filtered by ward's taluk for convenience
    localbodies = tbl_localbody.objects.filter(TalukId=ward.LocalbodyID.TalukId_id)
    return render(request, 'admin/waed_edit.html', {
        'ward': ward,
        'taluks': taluks,
        'localbodies': localbodies,
    })
    
def deleteward(request, wid):
    ward = tbl_ward.objects.get(WardID=wid)
    ward.delete()
    return redirect('viewward')

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

def viewsubcategory(request):
    categories = tbl_category.objects.all()
    subcategories = tbl_subcategory.objects.select_related('categoryID').all()
    return render(request, 'admin/subcategory_view.html', {
        'categories': categories,
        'subcategories': subcategories
    })

@require_http_methods(["GET"])
def filter_subcategory(request):
    category_id = request.GET.get('category_id', '')
    subcategories = tbl_subcategory.objects.select_related('categoryID').all()
    if category_id:
        subcategories = subcategories.filter(categoryID=category_id)
    data = []
    for sc in subcategories:
        data.append({
            'SubCategoryID': sc.subCategoryId,
            'SubCategoryName': sc.SubCategoryname,
            'CategoryID': {
                'CategoryID': sc.categoryID.CategoryID,
                'CategoryName': sc.categoryID.CategoryName
            }
        })
    return JsonResponse(data, safe=False)

def editsubcategory(request, sid):
    categories = tbl_category.objects.all()
    subcategory = tbl_subcategory.objects.select_related('categoryID').get(subCategoryId=sid)
    if request.method == 'POST':
        subcatname = request.POST.get('subcategoryname')
        categoryid = request.POST.get('categoryid')
        subcategory.SubCategoryname = subcatname
        subcategory.categoryID = tbl_category.objects.get(CategoryID=categoryid)
        subcategory.save()
        categories = tbl_category.objects.all()
        subcategories = tbl_subcategory.objects.select_related('categoryID').all()
        return render(request, 'admin/subcategory_view.html', {
            'categories': categories,
            'subcategories': subcategories
        })
    else:
        subcategory = tbl_subcategory.objects.select_related('categoryID').get(subCategoryId=sid)
        return render(request, 'admin/editsubcategory.html', {
            'subcategory': subcategory,
            'categories': categories
        })
    
def deletesubcategory(request, sid):
    subcategory = tbl_subcategory.objects.get(subCategoryId=sid)
    subcategory.delete()
    return viewsubcategory(request)

# LocalBody Views
def viewlocalbody(request):
    taluks = tbl_taluk.objects.all()
    localbody_types = tbl_localbody_type.objects.all()
    localbodies = tbl_localbody.objects.all()
    return render(request, 'admin/localbodyview.html', {
        'taluks': taluks, 
        'localbody_types': localbody_types,
        'localbodies': localbodies
    })

@require_http_methods(["GET"])
def filter_localbody(request):
    taluk_id = request.GET.get('taluk_id', '')
    type_id = request.GET.get('type_id', '')
    
    localbodies = tbl_localbody.objects.all()
    
    if taluk_id:
        localbodies = localbodies.filter(TalukId=taluk_id)
    if type_id:
        localbodies = localbodies.filter(TypeID=type_id)
    
    data = []
    for lb in localbodies:
        data.append({
            'LocalbodyID': lb.LocalbodyID,
            'LocalbodyName': lb.LocalbodyName,
            'TypeName': lb.TypeID.TypeName,
            'TalukName': lb.TalukId.TalukName
        })
    
    return JsonResponse(data, safe=False)

def editlocalbody(request, id):
    taluks = tbl_taluk.objects.all()
    localbody_types = tbl_localbody_type.objects.all()
    localbody = tbl_localbody.objects.get(LocalbodyID=id)
    
    if request.method == 'POST':
        localbodyname = request.POST.get('localbodyname')
        talukid = request.POST.get('talukid')
        typeid = request.POST.get('localbodyid')
        
        localbody.LocalbodyName = localbodyname
        localbody.TalukId = tbl_taluk.objects.get(TalukID=talukid)
        localbody.TypeID = tbl_localbody_type.objects.get(TypeID=typeid)
        localbody.save()
        
        taluks = tbl_taluk.objects.all()
        localbody_types = tbl_localbody_type.objects.all()
        localbodies = tbl_localbody.objects.all()
        return render(request, 'admin/localbodyview.html', {
            'taluks': taluks, 
            'localbody_types': localbody_types,
            'localbodies': localbodies
        })
    else:
        return render(request, 'admin/editlocalbody.html', {
            'localbody': localbody,
            'taluks': taluks,
            'localbody_types': localbody_types
        })

def deletelocalbody(request, id):
    localbody = tbl_localbody.objects.get(LocalbodyID=id)
    localbody.delete()
    return viewlocalbody(request)

def viewngo(request):
    pending_count = tbl_login.objects.filter(Role='NGO', Status='Pending').count()
    approved_count = tbl_login.objects.filter(Role='NGO', Status='Approved').count()
    rejected_count = tbl_login.objects.filter(Role='NGO', Status='Rejected').count()

    q = request.GET.get('q', '').strip()

    # Show only NGOs whose login status is Pending
    ngos = (
        tbl_ngo_reg.objects
        .select_related('LoginId', 'TalukID', 'LocalbodyID')
        .filter(LoginId__Role='NGO', LoginId__Status='Pending')
        .order_by('NGOID')
    )

    if q:
        ngos = ngos.filter(Q(NGOname__icontains=q) | Q(Email__icontains=q))

    return render(request, 'admin/ngo_view.html', {
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'ngos': ngos,
    })

def approve_ngo(request, ngoid):
    try:
        ngo = tbl_ngo_reg.objects.select_related('LoginId').get(NGOID=ngoid)
    except tbl_ngo_reg.DoesNotExist:
        return redirect('viewngo')

    # Update login status to Approved
    login = ngo.LoginId
    login.Status = 'Approved'
    login.save()
    messages.success(request, f"Approved NGO '{ngo.NGOname}'.")
    return redirect('viewngo')


def reject_ngo(request, ngoid):
    try:
        ngo = tbl_ngo_reg.objects.select_related('LoginId').get(NGOID=ngoid)
    except tbl_ngo_reg.DoesNotExist:
        return redirect('viewngo')

    # Update login status to Rejected
    login = ngo.LoginId
    login.Status = 'Rejected'
    login.save()
    messages.info(request, f"Rejected NGO '{ngo.NGOname}'.")
    return redirect('viewngo')

def viewvolunteer(request):
    pending_count = tbl_login.objects.filter(Role='VOLUNTEER', Status='Pending').count()
    approved_count = tbl_login.objects.filter(Role='VOLUNTEER', Status='Approved').count()
    rejected_count = tbl_login.objects.filter(Role='VOLUNTEER', Status='Rejected').count()

    q = request.GET.get('q', '').strip()

    # Show only NGOs whose login status is Pending
    volunteers = (
        tbl_volunteer_reg.objects
        .select_related('LoginId', 'TalukID', 'LocalbodyID')
        .filter(LoginId__Role='VOLUNTEER', LoginId__Status='Pending')
        .order_by('VolunteerId')
    )

    if q:
        volunteers = volunteers.filter(Q(VolunteerName__icontains=q) | Q(Email__icontains=q))
    return render(request, 'admin/volunteer_view.html', {
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'volunteers': volunteers,
    })

def approve_vol(request, volid):
    try:
        volunteer = tbl_volunteer_reg.objects.select_related('LoginId').get(VolunteerId=volid)
    except tbl_volunteer_reg.DoesNotExist:
        return redirect('viewvolunteer')
    # Update login status to Approved
    login = volunteer.LoginId
    login.Status = 'Approved'
    login.save()
    messages.success(request, f"Approved Volunteer '{volunteer.Name}'.")
    return redirect('viewvolunteer')

def reject_vol(request, volid):
    try:
        volunteer = tbl_volunteer_reg.objects.select_related('LoginId').get(VolunteerId=volid)
    except tbl_volunteer_reg.DoesNotExist:
        return redirect('viewvolunteer')
    # Update login status to Rejected
    login = volunteer.LoginId
    login.Status = 'Rejected'
    login.save()
    messages.info(request, f"Rejected Volunteer '{volunteer.Name}'.")
    return redirect('viewvolunteer')










def disaster_reg(request):
    if request.method == 'POST':
        disastername = request.POST.get('disastername')
        disaster_obj = tbl_disaster()
        disaster_obj.DisasterName = disastername
        disaster_obj.save()
    return render(request, 'admin/disaster_reg.html')

def viewdisaster(request):
    disasters = tbl_disaster.objects.all()
    return render(request, 'admin/viewdisaster.html', {'disasters': disasters})

def editdisaster(request, did):
    disaster = tbl_disaster.objects.get(DisasterID=did)
    if request.method == 'POST':
        disastername = request.POST.get('disastername')
        disaster.DisasterName = disastername
        disaster.save()
        return redirect('viewdisaster')
    else:
        return render(request, 'admin/editdisaster.html', {'disaster': disaster})
    
def deletedisaster(request, did):
    disaster = tbl_disaster.objects.get(DisasterID=did)
    disaster.delete()
    return viewdisaster(request)

def service_reg(request):
    if request.method == 'POST':
        servicename = request.POST.get('servicename')
        service_obj = tbl_service_type()
        service_obj.serviceName = servicename
        service_obj.save()
    return render(request, 'admin/service_reg.html')

def viewservice(request):
    services = tbl_service_type.objects.all()
    return render(request, 'admin/viewservice.html', {'services': services})

def editservice(request, sid):
    service = tbl_service_type.objects.get(serviceID=sid)
    if request.method == 'POST':
        servicename = request.POST.get('servicename')
        service.serviceName = servicename
        service.save()
        return redirect('viewservice')
    else:
        return render(request, 'admin/service_edit.html', {'service': service})
    
def deleteservice(request, sid):
    service = tbl_service_type.objects.get(serviceID=sid)
    service.delete()
    return viewservice(request)