import random
import csv
import json
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import logout
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum, F, Count
from django.db.models.functions import Coalesce
from guestapp.models import tbl_login, tbl_ngo_reg, tbl_volunteer_reg, tbl_request, tbl_request_service, tbl_request_assignment, tbl_ngo_volunteer_assignment
from NGOapp.models import tbl_ngo_helptype
from .models import tbl_subcategory, tbl_category, tbl_taluk, tbl_localbody_type, tbl_localbody,  tbl_ward , tbl_disaster, tbl_service_type
from django.views.decorators.http import require_http_methods

# Create your views here.
def adminhome(request):
    return admin_control_hub(request)


BUSY_ASSIGNMENT_STATUSES = ['Pending', 'Accepted', 'Delivered', 'In Progress']


def _is_volunteer_busy(volunteer_id, exclude_assignment_id=None):
    busy_qs = tbl_request_assignment.objects.filter(
        volunteerID_id=volunteer_id,
        assignment_status__in=BUSY_ASSIGNMENT_STATUSES,
    )
    if exclude_assignment_id:
        busy_qs = busy_qs.exclude(assignmentID=exclude_assignment_id)
    return busy_qs.exists()


def _pick_ngo_external_volunteer(ngo_id, exclude_assignment_id=None):
    primary = tbl_ngo_volunteer_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_type='Permanent',
        status='Active',
        VolunteerID__LoginId__Status='Approved',
    ).select_related('VolunteerID').first()

    if primary and not _is_volunteer_busy(primary.VolunteerID_id, exclude_assignment_id):
        return primary.VolunteerID

    emergency_list = tbl_ngo_volunteer_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_type='Emergency',
        status='Active',
        VolunteerID__LoginId__Status='Approved',
    ).select_related('VolunteerID')

    for emergency in emergency_list:
        if not _is_volunteer_busy(emergency.VolunteerID_id, exclude_assignment_id):
            return emergency.VolunteerID

    return None


def _find_matching_ngo_for_service(req_service, taluk_id):
    candidates = tbl_ngo_reg.objects.filter(
        LoginID__Status='Approved',
        TalukID_id=taluk_id,
    )

    if req_service.serviceID_id:
        candidates = candidates.filter(
            tbl_ngo_helptype__serviceID_id=req_service.serviceID_id,
            tbl_ngo_helptype__isActive='Yes',
        )

    candidates = candidates.distinct().order_by('NGOID')
    if not candidates.exists():
        return None

    for ngo in candidates:
        has_internal = str(ngo.hasVolunteers or '').strip().lower() == 'yes'
        if has_internal:
            return ngo

        if _pick_ngo_external_volunteer(ngo.NGOID):
            return ngo

    return candidates.first()

#Taluk registration
def taluk_reg(request):
    if request.method == 'POST':
        talukname = request.POST.get('talukname', '').strip()
        
        # Validation
        errors = []
        
        # Check if taluk name is provided
        if not talukname:
            errors.append('Taluk name is required.')
        
        # Validate taluk name format (letters, spaces, and hyphens only)
        if talukname:
            if not all(c.isalpha() or c.isspace() or c == '-' for c in talukname):
                errors.append('Taluk name must contain only letters, spaces, and hyphens.')
            
            # Check length
            if len(talukname) < 2:
                errors.append('Taluk name must be at least 2 characters long.')
            elif len(talukname) > 100:
                errors.append('Taluk name cannot exceed 100 characters.')
            
            # Check for duplicate taluk name (case-insensitive)
            if tbl_taluk.objects.filter(TalukName__iexact=talukname).exists():
                errors.append(f'Taluk "{talukname}" already exists.')
        
        # If there are errors, display them
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Save the taluk
            try:
                taluk_obj = tbl_taluk()
                taluk_obj.TalukName = talukname
                taluk_obj.save()
                messages.success(request, f'Taluk "{talukname}" registered successfully!')
                return redirect('talukreg')
            except Exception as e:
                messages.error(request, f'Error saving taluk: {str(e)}')
    
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
        localbodyname = request.POST.get('localbodyname', '').strip()
        localbodyid = request.POST.get('localbodyid')
        talukid = request.POST.get('talukid')
        
        # Validation
        errors = []
        
        # Check if taluk is selected
        if not talukid:
            errors.append('Taluk is required.')
        
        # Validate taluk exists
        taluk_obj = None
        if talukid:
            try:
                taluk_obj = tbl_taluk.objects.get(TalukID=talukid)
            except tbl_taluk.DoesNotExist:
                errors.append('Invalid taluk selected.')
        
        # Check if local body type is selected
        if not localbodyid:
            errors.append('Local body type is required.')
        
        # Validate local body type exists
        localbody_type_obj = None
        if localbodyid:
            try:
                localbody_type_obj = tbl_localbody_type.objects.get(TypeID=localbodyid)
            except tbl_localbody_type.DoesNotExist:
                errors.append('Invalid local body type selected.')
        
        # Check if local body name is provided
        if not localbodyname:
            errors.append('Local body name is required.')
        
        # Validate local body name format
        if localbodyname:
            # Check if it contains only valid characters (letters, numbers, spaces, hyphens)
            if not all(c.isalnum() or c.isspace() or c == '-' for c in localbodyname):
                errors.append('Local body name must contain only letters, numbers, spaces, and hyphens.')
            
            # Check length
            if len(localbodyname) < 2:
                errors.append('Local body name must be at least 2 characters long.')
            elif len(localbodyname) > 100:
                errors.append('Local body name cannot exceed 100 characters.')
            
            # Check for duplicate local body name within the same taluk (case-insensitive)
            if talukid and tbl_localbody.objects.filter(
                LocalbodyName__iexact=localbodyname,
                TalukId=talukid
            ).exists():
                errors.append(f'Local body "{localbodyname}" already exists in this taluk.')
        
        # If there are errors, display them
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Save the local body
            try:
                localbody_obj = tbl_localbody()
                localbody_obj.LocalbodyName = localbodyname
                localbody_obj.TypeID = localbody_type_obj
                localbody_obj.TalukId = taluk_obj
                localbody_obj.save()
                messages.success(request, f'Local body "{localbodyname}" registered successfully!')
                return redirect('localbody')
            except Exception as e:
                messages.error(request, f'Error saving local body: {str(e)}')
    
    return render(request, 'admin/localbody_reg.html', {'taluks': taluks, 'localbodies': localbodies})

def ward_reg(request):
    taluks = tbl_taluk.objects.all()
    localbodies = tbl_localbody.objects.none()  # filled via JS after taluk select
    if request.method == 'POST':
        ward_number = request.POST.get('wardnumber', '').strip()
        localbody_id = request.POST.get('localbodyid')
        taluk_id = request.POST.get('talukid')
        
        # Validation
        errors = []
        
        # Check if all fields are filled
        if not ward_number:
            errors.append('Ward number is required.')
        if not localbody_id:
            errors.append('Local body is required.')
        if not taluk_id:
            errors.append('Taluk is required.')
        
        # Validate ward number format (alphanumeric, 1-10 characters)
        if ward_number:
            if not ward_number.replace(' ', '').isalnum():
                errors.append('Ward number must contain only letters and numbers.')
            if len(ward_number) > 10:
                errors.append('Ward number cannot exceed 10 characters.')
        
        # Check if localbody exists
        if localbody_id:
            try:
                localbody = tbl_localbody.objects.get(LocalbodyID=localbody_id)
            except tbl_localbody.DoesNotExist:
                errors.append('Invalid local body selected.')
                localbody = None
        else:
            localbody = None
        
        # Check for duplicate ward number in same local body
        if ward_number and localbody_id:
            if tbl_ward.objects.filter(WardNumber=ward_number, LocalbodyID=localbody_id).exists():
                errors.append(f'Ward number "{ward_number}" already exists in this local body.')
        
        # If there are errors, display them
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Save the ward
            try:
                ward_obj = tbl_ward()
                ward_obj.WardNumber = ward_number
                ward_obj.LocalbodyID = localbody
                ward_obj.save()
                messages.success(request, f'Ward "{ward_number}" registered successfully!')
                return redirect('wardreg')
            except Exception as e:
                messages.error(request, f'Error saving ward: {str(e)}')
    
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
        catname = request.POST.get('catname', '').strip()
        
        # Validation
        errors = []
        
        # Check if category name is provided
        if not catname:
            errors.append('Category name is required.')
        
        # Validate category name format
        if catname:
            # Check if it contains only valid characters (letters, numbers, spaces, hyphens)
            if not all(c.isalnum() or c.isspace() or c == '-' for c in catname):
                errors.append('Category name must contain only letters, numbers, spaces, and hyphens.')
            
            # Check length
            if len(catname) < 2:
                errors.append('Category name must be at least 2 characters long.')
            elif len(catname) > 100:
                errors.append('Category name cannot exceed 100 characters.')
            
            # Check for duplicate category name (case-insensitive)
            if tbl_category.objects.filter(CategoryName__iexact=catname).exists():
                errors.append(f'Category "{catname}" already exists.')
        
        # If there are errors, display them
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Save the category
            try:
                cat_obj = tbl_category()
                cat_obj.CategoryName = catname
                cat_obj.save()
                messages.success(request, f'Category "{catname}" registered successfully!')
                return redirect('catreg')
            except Exception as e:
                messages.error(request, f'Error saving category: {str(e)}')
    
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
        subcatname = request.POST.get('subcatname', '').strip()
        categoryid = request.POST.get('categoryid')
        min_required_quantity = request.POST.get('min_required_quantity', '').strip()
        
        # Validation
        errors = []
        
        # Check if category is selected
        if not categoryid:
            errors.append('Category is required.')
        
        # Validate category exists
        category_obj = None
        if categoryid:
            try:
                category_obj = tbl_category.objects.get(CategoryID=categoryid)
            except tbl_category.DoesNotExist:
                errors.append('Invalid category selected.')
        
        # Check if subcategory name is provided
        if not subcatname:
            errors.append('Subcategory name is required.')
        
        # Validate subcategory name format
        if subcatname:
            # Check if it contains only valid characters (letters, numbers, spaces, hyphens)
            if not all(c.isalnum() or c.isspace() or c == '-' for c in subcatname):
                errors.append('Subcategory name must contain only letters, numbers, spaces, and hyphens.')
            
            # Check length
            if len(subcatname) < 2:
                errors.append('Subcategory name must be at least 2 characters long.')
            elif len(subcatname) > 100:
                errors.append('Subcategory name cannot exceed 100 characters.')
            
            # Check for duplicate subcategory name within the same category (case-insensitive)
            if categoryid and tbl_subcategory.objects.filter(
                SubCategoryname__iexact=subcatname, 
                categoryID=categoryid
            ).exists():
                errors.append(f'Subcategory "{subcatname}" already exists in this category.')
        
        # Validate minimum required quantity
        if not min_required_quantity:
            errors.append('Minimum required quantity is required.')
        else:
            try:
                min_qty = int(min_required_quantity)
                if min_qty < 0:
                    errors.append('Minimum required quantity must be 0 or greater.')
            except ValueError:
                errors.append('Minimum required quantity must be a valid number.')
        
        # If there are errors, display them
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Save the subcategory
            try:
                subcat_obj = tbl_subcategory()
                subcat_obj.SubCategoryname = subcatname
                subcat_obj.categoryID = category_obj
                subcat_obj.min_required_quantity = int(min_required_quantity)
                subcat_obj.save()
                messages.success(request, f'Subcategory "{subcatname}" registered successfully!')
                return redirect('subcatreg')
            except Exception as e:
                messages.error(request, f'Error saving subcategory: {str(e)}')
    
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
            'MinRequiredQuantity': sc.min_required_quantity,
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

    # Get volunteer statistics
    total_volunteers = tbl_volunteer_reg.objects.filter(LoginId__Status='Approved').count()
    available_volunteers = tbl_volunteer_reg.objects.filter(
        LoginId__Status='Approved',
        availability_status='Available'
    ).count()

    q = request.GET.get('q', '').strip()

    # Show only NGOs whose login status is Pending
    ngos = (
        tbl_ngo_reg.objects
        .select_related('LoginID', 'TalukID', 'LocalbodyID')
        .prefetch_related('tbl_ngo_volunteer_assignment_set')
        .filter(LoginID__Role='NGO', LoginID__Status='Pending')
        .order_by('NGOID')
    )

    if q:
        ngos = ngos.filter(Q(NGOname__icontains=q) | Q(Email__icontains=q))

    # Add assigned volunteer info to each NGO
    for ngo in ngos:
        assigned = ngo.tbl_ngo_volunteer_assignment_set.filter(status='Active').first()
        ngo.assigned_volunteer = assigned

    return render(request, 'admin/ngo_view.html', {
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'ngos': ngos,
        'total_volunteers': total_volunteers,
        'available_volunteers': available_volunteers,
    })

def assign_volunteer_to_ngo(request, ngoid):
    try:
        ngo = tbl_ngo_reg.objects.select_related('LoginID', 'TalukID', 'LocalbodyID').get(NGOID=ngoid)
    except tbl_ngo_reg.DoesNotExist:
        messages.error(request, "NGO not found.")
        return redirect('viewngo')

    # Check if volunteer is already assigned
    assigned_volunteer = tbl_ngo_volunteer_assignment.objects.filter(
        NGOID=ngoid,
        status='Active'
    ).select_related('VolunteerID').first()

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Handle unassign action
        if action == 'unassign':
            tbl_ngo_volunteer_assignment.objects.filter(
                NGOID=ngoid,
                status='Active'
            ).delete()
            messages.success(request, f"Volunteer unassigned from '{ngo.NGOname}'.")
            return redirect('viewngo')
        
        # Handle assign action
        volunteer_id = request.POST.get('volunteer_id')
        
        if not volunteer_id:
            messages.error(request, 'Please select a volunteer.')
        else:
            try:
                volunteer = tbl_volunteer_reg.objects.get(VolunteerId=volunteer_id)
                
                # Check if this volunteer is already assigned to another NGO
                existing_assignment = tbl_ngo_volunteer_assignment.objects.filter(
                    VolunteerID=volunteer_id,
                    status='Active'
                ).exists()
                
                if existing_assignment:
                    messages.error(request, f"Volunteer '{volunteer.Name}' is already assigned to another NGO.")
                else:
                    # Create or update assignment
                    tbl_ngo_volunteer_assignment.objects.update_or_create(
                        NGOID=ngo,
                        VolunteerID=volunteer,
                        defaults={'assignment_type': 'Permanent', 'status': 'Active'}
                    )

                    if ngo.Email:
                        try:
                            send_mail(
                                subject='ResQLink Volunteer Assignment Update',
                                message=(
                                    f"Dear {ngo.NGOname},\n\n"
                                    "A volunteer has now been assigned to your NGO.\n\n"
                                    f"Assigned Volunteer: {volunteer.Name}\n"
                                    f"Contact: {volunteer.ContactNumber1}\n"
                                    f"Email: {volunteer.Email}\n\n"
                                    "Please coordinate through your dashboard for response activities.\n\n"
                                    "Regards,\n"
                                    "ResQLink Admin Team"
                                ),
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[ngo.Email],
                                fail_silently=False
                            )
                        except Exception as e:
                            messages.warning(
                                request,
                                f"Volunteer assigned, but assignment email could not be sent to {ngo.Email}: {str(e)}"
                            )

                    messages.success(request, f"Volunteer '{volunteer.Name}' assigned to '{ngo.NGOname}' successfully!")
                    return redirect('viewngo')
            except tbl_volunteer_reg.DoesNotExist:
                messages.error(request, "Selected volunteer not found.")

    # Get available volunteers from same LocalBody
    # Exclude volunteers already assigned to any NGO (one volunteer = one NGO only)
    available_volunteers = tbl_volunteer_reg.objects.filter(
        LocalbodyID=ngo.LocalbodyID,
        LoginId__Status='Approved',
        availability_status='Available'
    ).exclude(
        tbl_ngo_volunteer_assignment__status='Active'
    ).distinct()

    return render(request, 'admin/assign_volunteer.html', {
        'ngo': ngo,
        'available_volunteers': available_volunteers,
        'assigned_volunteer': assigned_volunteer,
    })

def approve_ngo(request, ngoid):
    try:
        ngo = tbl_ngo_reg.objects.select_related('LoginID').get(NGOID=ngoid)
    except tbl_ngo_reg.DoesNotExist:
        return redirect('viewngo')

    was_already_approved = ngo.LoginID.Status == 'Approved'

    # Update login status to Approved
    login = ngo.LoginID
    login.Status = 'Approved'
    login.save()

    if not was_already_approved and ngo.Email:
        has_internal_volunteers = str(ngo.hasVolunteers or '').strip().lower() == 'yes'

        assigned_volunteer = tbl_ngo_volunteer_assignment.objects.filter(
            NGOID=ngo,
            status='Active'
        ).select_related('VolunteerID').first()

        if assigned_volunteer and assigned_volunteer.VolunteerID:
            assignment_message = f"Assigned Volunteer: {assigned_volunteer.VolunteerID.Name}"
        elif has_internal_volunteers:
            assignment_message = "You have opted to use NGO internal volunteers. External volunteer assignment is not required."
        else:
            assignment_message = "No volunteer is assigned yet. You will receive a mail later about the assignment."

        try:
            send_mail(
                subject='ResQLink NGO Approval Confirmation',
                message=(
                    f"Dear {ngo.NGOname},\n\n"
                    "Your NGO registration with ResQLink has been approved.\n\n"
                    f"{assignment_message}\n\n"
                    "Thank you for partnering with us in disaster response efforts.\n\n"
                    "Regards,\n"
                    "ResQLink Admin Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[ngo.Email],
                fail_silently=False
            )
        except Exception as e:
            messages.warning(
                request,
                f"NGO approved, but approval email could not be sent to {ngo.Email}: {str(e)}"
            )

    messages.success(request, f"Approved NGO '{ngo.NGOname}'. You can now assign volunteers from the Manage NGO Volunteers page.")
    return redirect('viewngo')


def reject_ngo(request, ngoid):
    try:
        ngo = tbl_ngo_reg.objects.select_related('LoginID').get(NGOID=ngoid)
    except tbl_ngo_reg.DoesNotExist:
        return redirect('viewngo')

    # Update login status to Rejected
    login = ngo.LoginID
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

def approved_volunteer_list(request):
    volunteers = (
        tbl_volunteer_reg.objects
        .select_related('LoginId', 'TalukID', 'LocalbodyID')
        .filter(LoginId__Role='VOLUNTEER', LoginId__Status='Approved')
        .order_by('VolunteerId')
    )
    return render(request, 'admin/approved_volunteer_view.html', {
        'volunteers': volunteers
    })


def approve_vol(request, volid):
    try:
        volunteer = tbl_volunteer_reg.objects.select_related('LoginId').get(VolunteerId=volid)
    except tbl_volunteer_reg.DoesNotExist:
        return redirect('viewvolunteer')

    was_already_approved = volunteer.LoginId.Status == 'Approved'

    # Update login status to Approved
    login = volunteer.LoginId
    login.Status = 'Approved'
    login.save()

    if not was_already_approved and volunteer.Email:
        try:
            send_mail(
                subject='ResQLink Volunteer Approval Confirmation',
                message=(
                    f"Dear {volunteer.Name},\n\n"
                    "Your volunteer registration with ResQLink has been approved. "
                    "You can now log in and start supporting disaster response activities.\n\n"
                    "Thank you for volunteering with us.\n\n"
                    "Regards,\n"
                    "ResQLink Admin Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[volunteer.Email],
                fail_silently=False
            )
        except Exception as e:
            messages.warning(
                request,
                f"Volunteer approved, but approval email could not be sent to {volunteer.Email}: {str(e)}"
            )

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
        disastername = request.POST.get('disastername', '').strip()
        
        # Validation
        errors = []
        
        # Check if disaster name is provided
        if not disastername:
            errors.append('Disaster name is required.')
        
        # Validate disaster name format
        if disastername:
            # Check if it contains only valid characters (letters, numbers, spaces, hyphens)
            if not all(c.isalnum() or c.isspace() or c == '-' for c in disastername):
                errors.append('Disaster name must contain only letters, numbers, spaces, and hyphens.')
            
            # Check length
            if len(disastername) < 2:
                errors.append('Disaster name must be at least 2 characters long.')
            elif len(disastername) > 100:
                errors.append('Disaster name cannot exceed 100 characters.')
            
            # Check for duplicate disaster name (case-insensitive)
            if tbl_disaster.objects.filter(DisasterName__iexact=disastername).exists():
                errors.append(f'Disaster "{disastername}" already exists.')
        
        # If there are errors, display them
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Save the disaster
            try:
                disaster_obj = tbl_disaster()
                disaster_obj.DisasterName = disastername
                disaster_obj.save()
                messages.success(request, f'Disaster "{disastername}" registered successfully!')
                return redirect('disasterreg')
            except Exception as e:
                messages.error(request, f'Error saving disaster: {str(e)}')
    
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
        servicename = request.POST.get('servicename', '').strip()
        
        # Validation
        errors = []
        
        # Check if service name is provided
        if not servicename:
            errors.append('Service name is required.')
        
        # Validate service name format
        if servicename:
            # Check if it contains only valid characters (letters, numbers, spaces, hyphens)
            if not all(c.isalnum() or c.isspace() or c == '-' for c in servicename):
                errors.append('Service name must contain only letters, numbers, spaces, and hyphens.')
            
            # Check length
            if len(servicename) < 2:
                errors.append('Service name must be at least 2 characters long.')
            elif len(servicename) > 100:
                errors.append('Service name cannot exceed 100 characters.')
            
            # Check for duplicate service name (case-insensitive)
            if tbl_service_type.objects.filter(serviceName__iexact=servicename).exists():
                errors.append(f'Service "{servicename}" already exists.')
        
        # If there are errors, display them
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Save the service
            try:
                service_obj = tbl_service_type()
                service_obj.serviceName = servicename
                service_obj.save()
                messages.success(request, f'Service "{servicename}" registered successfully!')
                return redirect('servicereg')
            except Exception as e:
                messages.error(request, f'Error saving service: {str(e)}')
    
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

def admin_view_ngo_stock(request):
    inventory = tbl_ngo_helptype.objects.select_related(
        'NGOID', 'categoryID', 'subCategoryID', 'serviceID'
    ).filter(isActive='Yes').order_by('NGOID__NGOname', 'categoryID__CategoryName', 'serviceID__serviceName', 'subCategoryID__SubCategoryname')

    ngo_wise_inventory_map = {}
    for item in inventory:
        ngo_id = item.NGOID_id
        if ngo_id not in ngo_wise_inventory_map:
            ngo_wise_inventory_map[ngo_id] = {
                'ngo': item.NGOID,
                'items': [],
            }
        ngo_wise_inventory_map[ngo_id]['items'].append(item)

    ngo_wise_inventory = list(ngo_wise_inventory_map.values())

    # Same "Shrinking" logic for the Admin's Global Alert section
    shortage_summary = tbl_request_service.objects.filter(
        requestID__request_type='community'
    ).exclude(
        status='Fully Assigned'
    ).values('subCategoryID__SubCategoryname').annotate(
        total_requested=Sum('quantity'),
        total_assigned=Coalesce(Sum('tbl_request_assignment__assigned_quntity'), 0)
    ).annotate(
        remaining_shortage=F('total_requested') - F('total_assigned')
    ).filter(remaining_shortage__gt=0)

    return render(request, 'admin/view_ngo_stock.html', {
        'inventory': inventory, 
        'ngo_wise_inventory': ngo_wise_inventory,
        'shortages': shortage_summary
    })

from django.db.models import Sum

def view_community_requests(request):
    requests = tbl_request.objects.filter(request_type='community').prefetch_related('tbl_request_service_set')

    for r in requests:
        # Check if any item in this request has a shortage that can now be filled
        r.new_stock_available = False
        
        if 'Partially' in r.request_status:
            items_with_shortage = r.tbl_request_service_set.exclude(status='Fully Assigned')
            for item in items_with_shortage:
                # Calculate how much is missing
                shortage = (item.quantity or 0) - (item.fulfilled_quantity or 0)
                
                # Check if any NGO has this item in stock right now
                current_stock = tbl_ngo_helptype.objects.filter(
                    subCategoryID=item.subCategoryID, 
                    isActive='Yes'
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                # If there is at least 1 item in stock, show the "Allocate Remaining" button
                if int(current_stock) > 0:
                    r.new_stock_available = True
                    break

    return render(request, 'admin/community_request.html', {'requests': requests})
def approve_community_request(request, reqid):
    if request.method == "POST":
        print(f"\n--- DEBUG START: Processing Request #{reqid} ---")
        try:
            parent_request = tbl_request.objects.get(request_id=reqid)
            requested_items = tbl_request_service.objects.filter(requestID=parent_request)
        except tbl_request.DoesNotExist:
            messages.error(request, "Request not found.")
            return redirect('viewrequest')

        # Mark the community request as verified when admin approves it
        if parent_request.campID:
            parent_request.campID.is_verified = 'Yes'
            parent_request.campID.save()
            print(f"--- Community Request '{parent_request.campID.community_name}' marked as VERIFIED ---")
            print(f"--- Camp ID: {parent_request.campID.campID}, is_verified: {parent_request.campID.is_verified} ---")

        # This map tracks volunteers picked during THIS specific click session
        ngo_volunteer_map = {}
        all_items_fully_satisfied = True 
        any_allocation_made = False

        for item in requested_items:
            # 1. Calculate the actual shortage
            # Shortage = (Total Requested) - (What we already assigned in previous rounds)
            total_needed = item.quantity if item.quantity else 0
            
            # Use getattr in case fulfilled_quantity isn't initialized yet
            already_fulfilled = getattr(item, 'fulfilled_quantity', 0) 
            remaining_to_fulfill = total_needed - already_fulfilled

            if remaining_to_fulfill <= 0:
                print(f"Skipping {item.subCategoryID.SubCategoryname}: Already Fully Satisfied.")
                continue 

            print(f"\nProcessing Item: {item.subCategoryID.SubCategoryname} | Remaining Needed: {remaining_to_fulfill}")

            # 2. Find NGOs that have stock for this specific subcategory
            eligible_ngos = tbl_ngo_helptype.objects.filter(
                subCategoryID=item.subCategoryID,
                isActive='Yes'
            ).order_by('-quantity') 

            for stock_record in eligible_ngos:
                if remaining_to_fulfill <= 0:
                    break
                
                try: 
                    current_stock = int(stock_record.quantity)
                except: 
                    current_stock = 0
                
                if current_stock <= 0:
                    continue

                # Calculate how much this NGO can contribute to the remaining shortage
                allocation = min(remaining_to_fulfill, current_stock)
                
                if allocation > 0:
                    any_allocation_made = True
                    # Create the assignment record
                    assignment = tbl_request_assignment.objects.create(
                        NGOID=stock_record.NGOID,
                        request_serviceID=item,
                        assigned_quntity=allocation,
                        assignment_status='Accepted'
                    )
                    print(f"--- Created Assignment ID: {assignment.assignmentID} for NGO: {stock_record.NGOID.NGOname} (ID: {stock_record.NGOID.NGOID}) ---")
                    print(f"    Item: {item.subCategoryID.SubCategoryname}, Qty: {allocation}, Status: Accepted ---")
                    
                    # Deduct stock from NGO Warehouse
                    stock_record.quantity = str(current_stock - allocation)
                    stock_record.save()

                    # Update the fulfilled count on the service record
                    item.fulfilled_quantity = (item.fulfilled_quantity or 0) + allocation
                    remaining_to_fulfill -= allocation

                    # --- VOLUNTEER LOGIC ---
                    if str(stock_record.NGOID.hasVolunteers).strip().lower() == 'no':
                        ngo_id = stock_record.NGOID.NGOID
                        
                        # Reuse volunteer if already picked for this NGO in this session or previous rounds
                        if ngo_id in ngo_volunteer_map:
                            assignment.volunteerID = ngo_volunteer_map[ngo_id]
                        else:
                            existing_assignment = tbl_request_assignment.objects.filter(
                                NGOID=stock_record.NGOID,
                                request_serviceID__requestID=parent_request,
                                volunteerID__isnull=False
                            ).first()

                            if existing_assignment:
                                assignment.volunteerID = existing_assignment.volunteerID
                                ngo_volunteer_map[ngo_id] = assignment.volunteerID 
                            else:
                                # COMMUNITY FLOW WITH FALLBACKS:
                                # Local Body -> Taluk -> Global Available -> Global Approved (last resort)
                                vols = tbl_volunteer_reg.objects.filter(
                                    LocalbodyID=parent_request.campID.localbodyID,
                                    availability_status='Available',
                                    LoginId__Status='Approved'
                                )

                                if not vols.exists():
                                    vols = tbl_volunteer_reg.objects.filter(
                                        TalukID=parent_request.campID.talukID,
                                        availability_status='Available',
                                        LoginId__Status='Approved'
                                    )

                                if not vols.exists():
                                    vols = tbl_volunteer_reg.objects.filter(
                                        availability_status='Available',
                                        LoginId__Status='Approved'
                                    )

                                if not vols.exists():
                                    vols = tbl_volunteer_reg.objects.filter(
                                        LoginId__Status='Approved'
                                    )

                                if vols.exists():
                                    selected_vol = random.choice(list(vols))
                                    assignment.volunteerID = selected_vol
                                    selected_vol.availability_status = 'Busy'
                                    selected_vol.save()
                                    ngo_volunteer_map[ngo_id] = selected_vol
                        
                        assignment.save()

                    # --- EMAIL NOTIFICATION ---
                    try:
                        send_mail(
                            f"Urgent Resource Allocation: {parent_request.campID.community_name}",
                            f"Please deliver {allocation} {item.subCategoryID.SubCategoryname} to {parent_request.campID.community_name}.",
                            'sandra7145dev@gmail.com',
                            [stock_record.NGOID.Email],
                            fail_silently=True
                        )
                    except: pass

            # 3. Update Item Level Status
            if item.fulfilled_quantity >= total_needed:
                item.status = 'Fully Assigned'
            elif item.fulfilled_quantity > 0:
                shortage = total_needed - item.fulfilled_quantity
                item.status = f'Partially Assigned (Shortage: {shortage})'
                all_items_fully_satisfied = False
            else:
                item.status = 'Not Assigned (Out of Stock)'
                all_items_fully_satisfied = False
            
            item.save()

        # 4. Update Parent Request Status
        if all_items_fully_satisfied:
            parent_request.request_status = 'Approved - Fully Assigned'
        else:
            parent_request.request_status = 'Approved - Partially Assigned'
        
        parent_request.save()

        if any_allocation_made:
            messages.success(request, f"Allocation processed for Request #{reqid}.")
        else:
            messages.warning(request, "No new allocations possible with current NGO stock.")
        
    return redirect('viewrequest')
def export_ngo_stock_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="NGO_Stock_Summary_By_Category.csv"'

    writer = csv.writer(response)
    writer.writerow(['NGO Name', 'Category', 'Sub-Category', 'Quantity', 'Contact Email'])

    inventory = tbl_ngo_helptype.objects.select_related('NGOID', 'categoryID', 'subCategoryID').filter(isActive='Yes')

    # This dictionary will store totals like: {'Rice': 500, 'Water': 1200}
    subcategory_totals = {}

    for item in inventory:
        # Data Safety
        ngo_name = item.NGOID.NGOname if item.NGOID else "Unknown NGO"
        cat_name = item.categoryID.CategoryName if item.categoryID else "Uncategorized"
        sub_cat_name = item.subCategoryID.SubCategoryname if item.subCategoryID else "General"
        email = item.NGOID.Email if item.NGOID else "N/A"
        
        try:
            qty = int(item.quantity)
        except (ValueError, TypeError):
            qty = 0

        # Update the dictionary for the summary
        if sub_cat_name in subcategory_totals:
            subcategory_totals[sub_cat_name] += qty
        else:
            subcategory_totals[sub_cat_name] = qty

        writer.writerow([ngo_name, cat_name, sub_cat_name, qty, email])

    # Add spacing
    writer.writerow([])
    writer.writerow(['--- CATEGORY WISE SUMMARY ---'])
    writer.writerow(['Sub-Category', 'Total Available Quantity'])

    # Loop through our dictionary to write the summary rows
    for sub_cat, total in subcategory_totals.items():
        writer.writerow([sub_cat, total])

    return response

def admin_dashboard_charts(request):
    # Count statuses for the pie chart
    pending = tbl_request.objects.filter(request_status='Pending').count()
    fully = tbl_request.objects.filter(request_status='Approved - Fully Assigned').count()
    partially = tbl_request.objects.filter(request_status='Approved - Partially Assigned').count()
    
    context = {
        'pending': pending,
        'fully': fully,
        'partially': partially,
    }
    return render(request, 'admin/index.html', context)

def notify_shortage_global(request):
    # 1. Reset old broadcasts
    tbl_subcategory.objects.all().update(is_broadcasted=False)
    
    # Get subcategories that have a safety goal set
    subcategories = tbl_subcategory.objects.filter(min_required_quantity__gt=0)
    
    msg_body = "URGENT: ResQLink District Resource Alert\n"
    msg_body += "========================================\n\n"
    msg_body += "The following resources are currently in shortage:\n\n"
    found_shortage = False

    # Check for general safety buffer shortages
    for sub in subcategories:
        # Calculate current total stock in all NGO warehouses
        current_stock_sum = tbl_ngo_helptype.objects.filter(
            subCategoryID=sub, 
            isActive='Yes'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Logic to handle if quantity is stored as a string or integer
        try:
            warehouse_qty = int(current_stock_sum)
        except (ValueError, TypeError):
            warehouse_qty = 0

        # If stock is below the safety goal, mark for broadcast
        if warehouse_qty < sub.min_required_quantity:
            remaining = sub.min_required_quantity - warehouse_qty
            sub.is_broadcasted = True
            sub.save()
            
            msg_body += f"- {sub.SubCategoryname}: {remaining} units needed (Goal: {sub.min_required_quantity})\n"
            found_shortage = True

    # 2. Check for specific "Out of Stock" emergency requests
    out_of_stock_requests = tbl_request_service.objects.filter(
        requestID__request_status='Out of Stock'
    ).values('subCategoryID__SubCategoryname').annotate(total=Sum('quantity'))

    if out_of_stock_requests.exists():
        msg_body += "\nIMMEDIATE EMERGENCY NEEDS (Unfulfilled Requests):\n"
        for req in out_of_stock_requests:
            msg_body += f"- {req['subCategoryID__SubCategoryname']}: {req['total']} units needed immediately\n"
            found_shortage = True

    if not found_shortage:
        messages.info(request, "No shortages detected. All resources are above safety levels.")
        return redirect('view_ngo_stock')

    # 3. Send Email to ALL Approved NGOs
    msg_body += "\n\nPlease log in to the ResQLink NGO portal to update your stock and assist in relief efforts."
    
    # We filter by LoginID__Status to ensure we only email active, approved partners
    ngo_emails = list(tbl_ngo_reg.objects.filter(
        LoginID__Status='Approved'
    ).values_list('Email', flat=True))

    if ngo_emails:
        try:
            send_mail(
                "Urgent: ResQLink District Resource Shortage", 
                msg_body, 
                'sandra7145dev@gmail.com', # Your sender email
                ngo_emails, 
                fail_silently=False
            )
            messages.success(request, f"Broadcast successfully sent to {len(ngo_emails)} NGOs.")
        except Exception as e:
            messages.error(request, f"Database updated, but Email failed: {str(e)}")
    else:
        messages.warning(request, "Broadcast marked in system, but no approved NGOs found to receive emails.")

    return redirect('view_ngo_stock')

def reset_broadcast_session(request):
    # This removes the 'Sent' lock from the session
    if 'last_broadcast_time' in request.session:
        del request.session['last_broadcast_time']
        messages.success(request, "Broadcast status reset! You can now send alerts again.")
    return redirect('view_ngo_stock')


def admin_control_hub(request):
    # 1. VOLUNTEER LEADERBOARD LOGIC
    volunteer_performance = tbl_request_assignment.objects.filter(
        assignment_status='Completed'
    ).values('volunteerID__Name').annotate(
        deliveries=Count('assignmentID')
    ).order_by('-deliveries')[:5]

    # 2. SUMMARY COUNTS
    # Count unique communities/camps that have submitted requests
    total_active_camps = tbl_request.objects.filter(
        request_type='community',
        campID__isnull=False
    ).values('campID__community_name').distinct().count()
    
    # Total approved NGOs
    total_ngos = tbl_login.objects.filter(Role='NGO',Status='Approved').count()
    
    # Calculate unique items currently in shortage
    shortage_count = tbl_request_service.objects.filter(
        requestID__request_type='community'
    ).exclude(status='Fully Assigned').values('subCategoryID').distinct().count()

    # Chart data for category distribution
    data_query = (
        tbl_request_service.objects.filter(categoryID__isnull=False)
        .values('categoryID__CategoryName')
        .annotate(total=Count('request_service_id'))
        .order_by('categoryID__CategoryName')
    )
    labels = [item['categoryID__CategoryName'] for item in data_query]
    counts = [item['total'] for item in data_query]

    # 3. REQUEST TYPE DISTRIBUTION (NEW: Community vs Individual)
    community_request_count = tbl_request.objects.filter(request_type='community').count()
    individual_request_count = tbl_request.objects.filter(request_type='individual').count()
    
    request_type_labels = []
    request_type_counts = []
    
    if community_request_count > 0:
        request_type_labels.append('Community Requests')
        request_type_counts.append(community_request_count)
    
    if individual_request_count > 0:
        request_type_labels.append('Individual Requests')
        request_type_counts.append(individual_request_count)

    context = {
        'performance': volunteer_performance,
        'camp_count': total_active_camps, # This now reflects unique community requests
        'ngo_count': total_ngos,
        'shortage_count': shortage_count,
        'labels_json': json.dumps(labels),
        'counts_json': json.dumps(counts),
        'request_type_labels_json': json.dumps(request_type_labels),
        'request_type_counts_json': json.dumps(request_type_counts),
    }

    return render(request, 'admin/index.html', context)

def approved_ngo_list(request):
    # Changed LoginId to LoginID to match your model
    ngos = tbl_ngo_reg.objects.filter(LoginID__Status='Approved').select_related('LoginID', 'LocalbodyID', 'TalukID')
    return render(request, 'admin/approved_ngo_view.html', {'ngos': ngos})

def view_ngo_profile(request, ngoid):
    # 1. Fetch the specific NGO details
    ngo = tbl_ngo_reg.objects.get(NGOID=ngoid)
    
    # 2. Fetch their inventory (Resources & Services)
    inventory = tbl_ngo_helptype.objects.filter(NGOID_id=ngoid, isActive='Yes').select_related('categoryID', 'subCategoryID', 'serviceID')
    
    # 3. Fetch assigned volunteer if any
    assigned_volunteer = tbl_ngo_volunteer_assignment.objects.filter(
        NGOID=ngoid,
        status='Active'
    ).select_related('VolunteerID').first()
    
    return render(request, 'admin/view_ngo_profile.html', {
        'ngo': ngo,
        'inventory': inventory,
        'assigned_volunteer': assigned_volunteer
    })


def view_volunteer_profile(request, volid):
    volunteer = tbl_volunteer_reg.objects.select_related('TalukID', 'LocalbodyID', 'LoginId').get(VolunteerId=volid)
    return render(request, 'admin/view_volunteer_profile.html', {
        'volunteer': volunteer
    })



def admin_dashboard(request):
    # --- 1. Category Distribution Logic (Pie Chart) ---
    data_query = tbl_request_service.objects.values('categoryID__CategoryName').annotate(total=Count('request_service_id'))
    labels = [item['categoryID__CategoryName'] for item in data_query]
    counts = [item['total'] for item in data_query]

    # --- 2. Fulfillment Status Logic (Bar Chart) - ADD THIS PART ---
    status_query = tbl_request.objects.values('request_status').annotate(total=Count('request_id'))
    status_labels = [item['request_status'] for item in status_query]
    status_counts = [item['total'] for item in status_query]

    # --- 3. Pass everything to the template ---
    return render(request, 'admin/dashboard.html', {
        'labels': labels,
        'counts': counts,
        'status_labels': status_labels, # New
        'status_counts': status_counts, # New
    })

def fix_community_verification(request):
    """
    Utility view to fix existing community requests that have been approved 
    but don't have is_verified='Yes'
    """
    from guestapp.models import tbl_community_request, tbl_request
    
    # Find all community requests that have approved status but aren't verified
    fixed_count = 0
    issues_found = []
    
    # Get all community requests
    all_community_requests = tbl_request.objects.filter(request_type='community').select_related('campID')
    
    print("\n=== COMMUNITY VERIFICATION FIX UTILITY ===")
    for req in all_community_requests:
        if req.campID:
            print(f"Request ID: {req.request_id}")
            print(f"  Community: {req.campID.community_name}")
            print(f"  Request Status: {req.request_status}")
            print(f"  Is Verified: '{req.campID.is_verified}'")
            
            # If request is approved but community is not verified, fix it
            if 'Approved' in req.request_status and req.campID.is_verified != 'Yes':
                req.campID.is_verified = 'Yes'
                req.campID.save()
                fixed_count += 1
                msg = f"Fixed: {req.campID.community_name} (Camp ID: {req.campID.campID}) - Now verified"
                issues_found.append(msg)
                print(f"  >>> {msg}")
            elif req.campID.is_verified == 'Yes':
                print(f"  OK: Already verified")
            else:
                print(f"  SKIPPED: Not approved yet")
        else:
            print(f"Request ID: {req.request_id} - WARNING: No campID!")
    
    print(f"\nTotal fixed: {fixed_count}")
    print("==========================================\n")
    
    if fixed_count > 0:
        messages.success(request, f"Fixed {fixed_count} community requests. They should now appear in NGO dashboards.")
    else:
        messages.info(request, "No issues found. All approved community requests are properly verified.")
    
    return redirect('viewrequest')

def view_completed_individual_requests(request):
    """
    View all completed individual requests with their assignment details
    """
    # Individual emergency flow uses assignment status for completion (not request_status)
    candidate_requests = (
        tbl_request.objects
        .filter(request_type='individual')
        .select_related('affectedID', 'affectedID__talukID', 'affectedID__localbodyID', 'disasterID')
        .prefetch_related('tbl_request_service_set', 'tbl_request_service_set__subCategoryID')
        .order_by('-request_id')
    )

    completed_requests = []
    in_progress_requests = []

    for req in candidate_requests:
        all_completed = True
        has_assignment = False

        for item in req.tbl_request_service_set.all():
            # Fetch fresh assignments directly from DB every time (avoid prefetch cache issues)
            # Only count assignments that were actually accepted/worked on, NOT initial 'Pending' ones
            assignments = tbl_request_assignment.objects.filter(
                request_serviceID=item
            ).exclude(assignment_status='Pending')

            if not assignments.exists():
                all_completed = False
                break

            has_assignment = True
            # Check if ALL accepted/worked-on assignments are Completed
            if any(a.assignment_status != 'Completed' for a in assignments):
                all_completed = False
                break

        req.is_fully_completed = all_completed and has_assignment
        if req.is_fully_completed:
            completed_requests.append(req)
        elif has_assignment:
            in_progress_requests.append(req)

    waiting_requests_raw = (
        tbl_request.objects
        .filter(request_type='individual', request_status='Pending')
        .select_related('affectedID', 'affectedID__talukID', 'affectedID__localbodyID', 'disasterID')
        .prefetch_related('tbl_request_service_set', 'tbl_request_service_set__serviceID')
        .order_by('-request_id')
    )

    # No need to check volunteer availability - NGO will handle that
    waiting_requests = list(waiting_requests_raw)

    waiting_assignments = (
        tbl_request_assignment.objects
        .filter(
            assignment_status='Waiting Admin Approval',
            request_serviceID__requestID__request_type='individual'
        )
        .select_related(
            'NGOID',
            'request_serviceID__requestID__affectedID',
            'request_serviceID__serviceID'
        )
        .order_by('-assignmentID')
    )

    # Show recently approved requests sent to NGOs
    # Exclude fully completed ones (they'll appear in Completed section)
    approved_requests_raw = (
        tbl_request.objects
        .filter(
            request_type='individual',
            request_status__in=['Pending NGO Approval', 'Approved']
        )
        .select_related('affectedID', 'affectedID__talukID', 'affectedID__localbodyID', 'NGOID', 'disasterID')
        .prefetch_related('tbl_request_service_set', 'tbl_request_service_set__serviceID')
        .order_by('-request_id')[:50]  # Get more to filter
    )

    # Filter out completed requests from approved list
    completed_request_ids = [r.request_id for r in completed_requests]
    approved_requests = [r for r in approved_requests_raw if r.request_id not in completed_request_ids][:20]

    return render(request, 'admin/completed_individual_requests.html', {
        'requests': completed_requests,
        'completed_requests': completed_requests,
        'in_progress_requests': in_progress_requests,
        'waiting_requests': waiting_requests,
        'waiting_assignments': waiting_assignments,
        'approved_requests': approved_requests,
    })


def approve_individual_request(request, reqid):
    if request.method != 'POST':
        return redirect('completed_individual_requests')

    try:
        req = tbl_request.objects.select_related('affectedID__talukID').get(
            request_id=reqid,
            request_type='individual',
        )
    except tbl_request.DoesNotExist:
        messages.error(request, 'Individual request not found.')
        return redirect('completed_individual_requests')

    if not req.affectedID:
        messages.error(request, 'Request location details are missing.')
        return redirect('completed_individual_requests')

    req_services = tbl_request_service.objects.filter(requestID=req)
    matched_count = 0
    selected_ngo = None

    for req_service in req_services:
        existing = tbl_request_assignment.objects.filter(request_serviceID=req_service).first()
        if existing:
            matched_count += 1
            selected_ngo = selected_ngo or existing.NGOID
            continue

        ngo = _find_matching_ngo_for_service(req_service, req.affectedID.talukID_id)
        if not ngo:
            continue

        # Create assignment - NGO will handle volunteer availability
        tbl_request_assignment.objects.create(
            NGOID=ngo,
            request_serviceID=req_service,
            assigned_quntity=1,
            assignment_status='Pending',
        )
        matched_count += 1
        selected_ngo = selected_ngo or ngo

    if matched_count == 0:
        req.request_status = 'Waiting NGO Match'
        req.save(update_fields=['request_status'])
        messages.warning(request, 'No suitable NGO found in the same taluk for this request.')
    else:
        req.request_status = 'Pending NGO Approval'
        if selected_ngo:
            req.NGOID = selected_ngo
            req.save(update_fields=['request_status', 'NGOID'])
        else:
            req.save(update_fields=['request_status'])
        messages.success(request, 'Request sent to matching NGO for approval.')

    return redirect('completed_individual_requests')


def approve_waiting_assignment(request, assignment_id):
    if request.method != 'POST':
        return redirect('completed_individual_requests')

    try:
        assignment = tbl_request_assignment.objects.select_related(
            'NGOID',
            'request_serviceID__requestID__affectedID',
            'request_serviceID__serviceID',
        ).get(
            assignmentID=assignment_id,
            assignment_status='Waiting Admin Approval',
            request_serviceID__requestID__request_type='individual',
        )
    except tbl_request_assignment.DoesNotExist:
        messages.error(request, 'Waiting assignment not found.')
        return redirect('completed_individual_requests')

    selected_volunteer = _pick_ngo_external_volunteer(
        assignment.NGOID_id,
        exclude_assignment_id=assignment.assignmentID,
    )

    if not selected_volunteer:
        messages.warning(request, 'All assigned NGO volunteers are still busy.')
        return redirect('completed_individual_requests')

    assignment.volunteerID = selected_volunteer
    assignment.assignment_status = 'Accepted'
    assignment.save(update_fields=['volunteerID', 'assignment_status'])

    selected_volunteer.availability_status = 'Busy'
    selected_volunteer.save(update_fields=['availability_status'])

    parent_request = assignment.request_serviceID.requestID
    parent_request.request_status = 'Approved'
    parent_request.save(update_fields=['request_status'])

    if selected_volunteer.Email:
        try:
            send_mail(
                subject='ResQLink Assignment Notification',
                message=(
                    f"Hello {selected_volunteer.Name},\n\n"
                    "A waiting request is now assigned to you by admin approval.\n"
                    "Please check your volunteer dashboard immediately."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[selected_volunteer.Email],
                fail_silently=True,
            )
        except Exception:
            pass

    messages.success(request, f"Volunteer {selected_volunteer.Name} assigned successfully.")
    return redirect('completed_individual_requests')

def manage_ngo_volunteers(request):
    """Manage volunteer assignments for approved NGOs"""
    # Get all approved NGOs with their volunteer assignments
    approved_ngos = tbl_ngo_reg.objects.filter(
        LoginID__Status='Approved'
    ).select_related(
        'LoginID', 'TalukID', 'LocalbodyID'
    ).prefetch_related('tbl_ngo_volunteer_assignment_set')
    
    q = request.GET.get('q', '').strip()
    if q:
        approved_ngos = approved_ngos.filter(Q(NGOname__icontains=q) | Q(Email__icontains=q))
    
    # Add assigned volunteers info to each NGO
    ngo_list = []
    for ngo in approved_ngos:
        permanent = ngo.tbl_ngo_volunteer_assignment_set.filter(
            assignment_type='Permanent', status='Active'
        ).select_related('VolunteerID').first()
        
        emergency = ngo.tbl_ngo_volunteer_assignment_set.filter(
            assignment_type='Emergency', status='Active'
        ).select_related('VolunteerID')
        
        ngo_list.append({
            'ngo': ngo,
            'permanent_volunteer': permanent,
            'emergency_volunteers': emergency
        })
    
    return render(request, 'admin/manage_ngo_volunteers.html', {
        'ngo_list': ngo_list,
        'total_ngos': len(ngo_list),
    })

def add_emergency_volunteer_to_ngo(request, ngoid):
    """Add emergency volunteer to an approved NGO"""
    try:
        ngo = tbl_ngo_reg.objects.select_related('LoginID', 'TalukID', 'LocalbodyID').get(NGOID=ngoid)
    except tbl_ngo_reg.DoesNotExist:
        messages.error(request, "NGO not found.")
        return redirect('manage_ngo_volunteers')
    
    # Check if NGO is approved
    if ngo.LoginID.Status != 'Approved':
        messages.error(request, "Only approved NGOs can have volunteers added.")
        return redirect('manage_ngo_volunteers')
    
    # Get current assignments
    permanent_volunteer = tbl_ngo_volunteer_assignment.objects.filter(
        NGOID=ngoid,
        assignment_type='Permanent',
        status='Active'
    ).select_related('VolunteerID').first()
    
    emergency_volunteers = tbl_ngo_volunteer_assignment.objects.filter(
        NGOID=ngoid,
        assignment_type='Emergency',
        status='Active'
    ).select_related('VolunteerID')
    
    if request.method == 'POST':
        volunteer_id = request.POST.get('volunteer_id')
        
        if not volunteer_id:
            messages.error(request, 'Please select a volunteer.')
        else:
            try:
                volunteer = tbl_volunteer_reg.objects.get(VolunteerId=volunteer_id)
                
                # Check if this volunteer is already assigned to another NGO (for any type)
                existing_assignment = tbl_ngo_volunteer_assignment.objects.filter(
                    VolunteerID=volunteer_id,
                    status='Active'
                ).exists()
                
                if existing_assignment:
                    messages.error(request, f"Volunteer '{volunteer.Name}' is already assigned to another NGO.")
                else:
                    # Check if this volunteer is already assigned as emergency to this NGO
                    duplicate = tbl_ngo_volunteer_assignment.objects.filter(
                        NGOID=ngoid,
                        VolunteerID=volunteer_id,
                        assignment_type='Emergency',
                        status='Active'
                    ).exists()
                    
                    if duplicate:
                        messages.error(request, f"Volunteer '{volunteer.Name}' is already added as emergency volunteer for this NGO.")
                    else:
                        # Create emergency assignment
                        tbl_ngo_volunteer_assignment.objects.create(
                            NGOID=ngo,
                            VolunteerID=volunteer,
                            assignment_type='Emergency',
                            status='Active'
                        )
                        messages.success(request, f"Emergency volunteer '{volunteer.Name}' added to '{ngo.NGOname}' successfully!")
                        return redirect('manage_ngo_volunteers')
            except tbl_volunteer_reg.DoesNotExist:
                messages.error(request, "Selected volunteer not found.")
    
    # Get available volunteers from same LocalBody
    # Exclude volunteers already assigned to any NGO
    available_volunteers = tbl_volunteer_reg.objects.filter(
        LocalbodyID=ngo.LocalbodyID,
        LoginId__Status='Approved',
        availability_status='Available'
    ).exclude(
        tbl_ngo_volunteer_assignment__status='Active'
    ).distinct()
    
    return render(request, 'admin/add_emergency_volunteer.html', {
        'ngo': ngo,
        'permanent_volunteer': permanent_volunteer,
        'emergency_volunteers': emergency_volunteers,
        'available_volunteers': available_volunteers,
    })

def remove_volunteer_assignment(request, assignment_id):
    """Remove a volunteer assignment (permanent or emergency)"""
    try:
        assignment = tbl_ngo_volunteer_assignment.objects.select_related('NGOID', 'VolunteerID').get(assignment_id=assignment_id)
        ngoid = assignment.NGOID.NGOID
        
        # Don't allow removing the only permanent volunteer
        if assignment.assignment_type == 'Permanent':
            messages.error(request, "Cannot remove the primary volunteer. Reassign a new one first.")
            return redirect('manage_ngo_volunteers')
        
        # Remove the assignment
        assignment.delete()
        messages.success(request, f"Volunteer '{assignment.VolunteerID.Name}' has been removed from '{assignment.NGOID.NGOname}'.")
    except tbl_ngo_volunteer_assignment.DoesNotExist:
        messages.error(request, "Assignment not found.")
    
    return redirect('manage_ngo_volunteers')

# Logout view
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('login')