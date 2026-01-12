from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from adminapp.models import tbl_category, tbl_subcategory, tbl_service_type
from guestapp.models import tbl_ngo_reg
from .models import tbl_ngo_helptype

# Create your views here.

def ngohome(request):
    categories = tbl_category.objects.all()
    service_types = tbl_service_type.objects.all()
    context = {
        'categories': categories,
        'service_types': service_types
    }
    return render(request, 'ngo/index.html', context)

def get_subcategories(request):
    category_id = request.GET.get('category_id')
    if category_id:
        subcategories = tbl_subcategory.objects.filter(categoryID=category_id).values('subCategoryId', 'SubCategoryname')
        data = [{'id': sub['subCategoryId'], 'name': sub['SubCategoryname']} for sub in subcategories]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


def submit_help_details(request):
    """Persist selected resources/services for the logged-in NGO."""
    if request.method != 'POST':
        return redirect('/NGOapp/ngohome/')

    login_id = request.session.get('LoginID')
    if not login_id:
        return redirect('/guestapp/login/')

    ngo = tbl_ngo_reg.objects.filter(LoginID_id=login_id).first()
    if not ngo:
        return HttpResponse('NGO not found for the logged-in user.', status=400)

    categories = request.POST.getlist('category[]')
    subcategories = request.POST.getlist('subcategory[]')
    service_types = request.POST.getlist('service_type[]')
    quantities = request.POST.getlist('quantity[]') if 'quantity[]' in request.POST else []

    records = []

    # Material resources rows
    for idx, (cat_id, sub_id) in enumerate(zip(categories, subcategories)):
        if cat_id and sub_id:
            qty = quantities[idx] if idx < len(quantities) else ''
            records.append(tbl_ngo_helptype(
                NGOID=ngo,
                categoryID_id=cat_id,
                subCategoryID_id=sub_id,
                serviceID=None,
                quantity=qty,
                isActive='Yes'
            ))

    # Non-material services rows
    for service_id in service_types:
        if service_id:
            records.append(tbl_ngo_helptype(
                NGOID=ngo,
                categoryID=None,
                subCategoryID=None,
                serviceID_id=service_id,
                quantity='',
                isActive='Yes'
            ))

    if records:
        tbl_ngo_helptype.objects.bulk_create(records)
        messages.success(request, 'Resources and services saved successfully.')
    else:
        messages.info(request, 'No items were submitted to save.')

    return redirect('/NGOapp/ngohome/')
