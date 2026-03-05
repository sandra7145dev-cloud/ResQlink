from django.db.models import IntegerField
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import logout
from adminapp.models import tbl_category, tbl_subcategory, tbl_service_type, tbl_localbody, tbl_ward, tbl_taluk
from guestapp.models import (
    tbl_ngo_reg,
    tbl_request,
    tbl_request_assignment,
    tbl_request_service,
    tbl_volunteer_reg,
    tbl_ngo_volunteer_assignment,
)
from .models import tbl_ngo_helptype
from django.core.mail import send_mail

# Create your views here.

from django.db.models import Sum, F
from django.db.models.functions import Coalesce, Cast


BUSY_ASSIGNMENT_STATUSES = ['Pending', 'Accepted', 'Delivered', 'In Progress']


def _is_volunteer_busy(volunteer_id, exclude_assignment_id=None):
    busy_qs = tbl_request_assignment.objects.filter(
        volunteerID_id=volunteer_id,
        assignment_status__in=BUSY_ASSIGNMENT_STATUSES,
    )
    if exclude_assignment_id:
        busy_qs = busy_qs.exclude(assignmentID=exclude_assignment_id)
    return busy_qs.exists()


def _pick_external_ngo_volunteer(ngo_id, assignment_id=None):
    # Primary volunteer has priority over emergency volunteers.
    primary_assignment = tbl_ngo_volunteer_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_type='Permanent',
        status='Active',
        VolunteerID__LoginId__Status='Approved',
    ).select_related('VolunteerID').first()

    if primary_assignment and not _is_volunteer_busy(primary_assignment.VolunteerID_id, assignment_id):
        return primary_assignment.VolunteerID

    emergency_assignments = tbl_ngo_volunteer_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_type='Emergency',
        status='Active',
        VolunteerID__LoginId__Status='Approved',
    ).select_related('VolunteerID')

    for emergency in emergency_assignments:
        if not _is_volunteer_busy(emergency.VolunteerID_id, assignment_id):
            return emergency.VolunteerID

    return None

def ngo_dashboard(request):
    ngo_id = request.session.get('ngo_id')
    
    # 1. INDIVIDUAL REQUEST LOGIC
    pending_service_ids = tbl_request_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_status='Pending',
        request_serviceID__requestID__request_type='individual',
    ).values_list('request_serviceID_id', flat=True)

    pending_items = tbl_request_service.objects.filter(
        request_service_id__in=pending_service_ids,
    ).select_related('requestID__affectedID', 'serviceID')

    # 2. COMMUNITY TASKS LOGIC - Only show verified community requests
    community_tasks = tbl_request_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_status__in=['Accepted', 'Delivered'],
        request_serviceID__requestID__request_type='community',
        request_serviceID__requestID__campID__is_verified='Yes'
    ).select_related('request_serviceID__requestID__campID', 'request_serviceID__subCategoryID')

    # 3. GLOBAL SAFETY BUFFER ALERTS (DATABASE-DRIVEN) - COMMENTED OUT
    # This section was responsible for displaying shortage alerts on the NGO dashboard
    # Kept admin broadcast email functionality but disabled front-end alert display
    shortage_alerts = []
    
    # # Fetch subcategories that the Admin has currently marked for Broadcast
    # broadcasted_items = tbl_subcategory.objects.filter(is_broadcasted=True)
    # 
    # for sub in broadcasted_items:
    #     # 1. We first Cast the text 'quantity' into an Integer
    #     # 2. Then we Sum those integers
    #     total_warehouse_stock = tbl_ngo_helptype.objects.filter(
    #         subCategoryID=sub, 
    #         isActive='Yes'
    #     ).annotate(
    #         qty_as_int=Cast('quantity', output_field=IntegerField())
    #     ).aggregate(
    #         total=Coalesce(Sum('qty_as_int'), 0)
    #     )['total']
    #     
    #     # The "Shrinking" Math: Goal (min_required_quantity) - Current Total Warehouse Stock
    #     remaining_needed = sub.min_required_quantity - int(total_warehouse_stock)
    #     
    #     # If the goal isn't met yet, show the alert
    #     if remaining_needed > 0:
    #         shortage_alerts.append({
    #             'subCategoryID__SubCategoryname': sub.SubCategoryname,
    #             'remaining_needed': remaining_needed,
    #             'target': sub.min_required_quantity,
    #             'available': total_warehouse_stock
    #         })
    #     else:
    #         # OPTIONAL: If the safety goal is met, turn off the broadcast flag automatically
    #         sub.is_broadcasted = False
    #         sub.save()

    # 4. DROPDOWN & STAT DATA
    context = {
        'pending_assignments': pending_items,
        'community_tasks': community_tasks,
        'shortage_alerts': shortage_alerts,
        'categories': tbl_category.objects.all(),
        'subcategories': tbl_subcategory.objects.all(),
        'taluks': tbl_taluk.objects.all(),
        'localbodies': tbl_localbody.objects.all(),
        'wards': tbl_ward.objects.all(),
        'service_types': tbl_service_type.objects.all(),
        'total_resources': tbl_ngo_helptype.objects.filter(NGOID_id=ngo_id, serviceID__isnull=True).count(),
        'total_services': tbl_ngo_helptype.objects.filter(NGOID_id=ngo_id, subCategoryID__isnull=True).count(),
    }
    
    return render(request, 'ngo/index.html', context)

def ngo_accept_reject_request(request):
    if request.method == "POST":
        ngo_id = request.session.get('ngo_id')
        req_service_id = request.POST.get('assignment_id') 
        action = request.POST.get('action')
        
        req_service = tbl_request_service.objects.get(request_service_id=req_service_id)
        parent_request = req_service.requestID
        assignment = tbl_request_assignment.objects.filter(
            NGOID_id=ngo_id,
            request_serviceID=req_service,
        ).first()

        if not assignment:
            assignment = tbl_request_assignment.objects.create(
                NGOID_id=ngo_id,
                request_serviceID=req_service,
                assigned_quntity=1,
                assignment_status='Pending',
            )

        if action == "reject":
            assignment.assignment_status = 'Rejected by NGO'
            assignment.save()
            messages.info(request, "Request rejected.")
            return redirect('/NGOapp/ngohome/')

        if action == "accept":
            if assignment.assignment_status in ['Accepted', 'Delivered', 'Completed']:
                messages.warning(request, "This request has already been accepted.")
                return redirect('/NGOapp/ngohome/')

            # 1. Update global request status and assignment state.
            parent_request.request_status = 'Approved'
            parent_request.NGOID_id = ngo_id
            parent_request.save()

            assignment.assignment_status = 'Accepted'
            assignment.assigned_quntity = assignment.assigned_quntity or 1
            assignment.save()

            # 2. External volunteer auto-assignment: Primary first, then Emergency.
            ngo = tbl_ngo_reg.objects.get(NGOID=ngo_id)
            has_volunteer_raw = str(ngo.hasVolunteers or '').strip().lower()

            if has_volunteer_raw == 'no':
                selected_volunteer = _pick_external_ngo_volunteer(ngo_id, assignment.assignmentID)
                if selected_volunteer:
                    assignment.volunteerID = selected_volunteer
                    assignment.assignment_status = 'Accepted'
                    assignment.save()

                    selected_volunteer.availability_status = 'Busy'
                    selected_volunteer.save()

                    if selected_volunteer.Email:
                        try:
                            subject = 'ResQLink Assignment Notification'
                            message = (
                                f"Hello {selected_volunteer.Name},\n\n"
                                f"A new request has been assigned to you.\n"
                                f"Requester: {parent_request.affectedID.name if parent_request.affectedID else 'N/A'}\n"
                                f"Service: {req_service.serviceID.serviceName if req_service.serviceID else 'General Help'}\n"
                                f"Please check your volunteer dashboard for details."
                            )
                            send_mail(
                                subject,
                                message,
                                'sandra7145dev@gmail.com',
                                [selected_volunteer.Email],
                                fail_silently=True,
                            )
                        except Exception:
                            pass

                    messages.success(request, f"Request accepted. Volunteer {selected_volunteer.Name} assigned.")
                else:
                    # All volunteers busy - mark as waiting and show in accepted tasks
                    assignment.volunteerID = None
                    assignment.assignment_status = 'Waiting Admin Approval'
                    assignment.save()
                    messages.warning(request, "Request accepted, but all volunteers are currently busy. You can assign a volunteer from Accepted Tasks when one becomes available.")
            else:
                messages.success(request, "Request accepted. Using NGO internal volunteers.")

        return redirect('/NGOapp/ngohome/')
    
def ngo_accepted_tasks(request):
    # 1. Get the logged-in NGO's ID from the session
    ngo_id = request.session.get('ngo_id')
    
    if not ngo_id:
        return redirect('login')

    # Show only active/finished accepted-task states; keep Pending in New Requests.
    accepted_list = tbl_request_assignment.objects.filter(
        NGOID=ngo_id,
        assignment_status__in=['Accepted', 'Delivered', 'Completed', 'Waiting Admin Approval'],
    ).exclude(
        request_serviceID__requestID__request_type='community',
        request_serviceID__requestID__campID__is_verified='No'
    ).select_related(
        'NGOID',
        'request_serviceID__requestID', 
        'request_serviceID__subCategoryID',
        'request_serviceID__serviceID',
        'request_serviceID__requestID__campID'
    )

    for task in accepted_list:
        task.can_assign_waiting_volunteer = False
        if task.assignment_status == 'Waiting Admin Approval':
            task.can_assign_waiting_volunteer = _pick_external_ngo_volunteer(
                ngo_id,
                task.assignmentID,
            ) is not None

    return render(request, 'ngo/accepted_task.html', {'accepted_list': accepted_list})


def ngo_assign_waiting_volunteer(request, aid):
    if request.method != 'POST':
        return redirect('ngo_accepted_tasks')

    ngo_id = request.session.get('ngo_id')
    if not ngo_id:
        return redirect('login')

    assignment = get_object_or_404(
        tbl_request_assignment,
        assignmentID=aid,
        NGOID_id=ngo_id,
        assignment_status='Waiting Admin Approval',
    )

    selected_volunteer = _pick_external_ngo_volunteer(ngo_id, assignment.assignmentID)
    if not selected_volunteer:
        messages.warning(request, 'No volunteers are free right now. Please try again shortly.')
        return redirect('ngo_accepted_tasks')

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
            subject = 'ResQLink Assignment Notification'
            service_name = 'General Help'
            if assignment.request_serviceID and assignment.request_serviceID.serviceID:
                service_name = assignment.request_serviceID.serviceID.serviceName
            message = (
                f"Hello {selected_volunteer.Name},\n\n"
                "A waiting request has now been assigned to you.\n"
                f"Service: {service_name}\n"
                "Please check your volunteer dashboard for details."
            )
            send_mail(
                subject,
                message,
                'sandra7145dev@gmail.com',
                [selected_volunteer.Email],
                fail_silently=True,
            )
        except Exception:
            pass

    messages.success(request, f"Volunteer {selected_volunteer.Name} assigned and notified.")
    return redirect('ngo_accepted_tasks')

# Logic to move a task from Pending to Accepted
def accept_task_action(request, aid):
    task = get_object_or_404(tbl_request_assignment, assignment_id=aid)
    task.assignment_status = 'Accepted'
    task.save()
    return redirect('ngo_accepted_tasks')

def ngo_complete_task(request, aid):
    if request.method == "POST":
        try:
            # 1. Fetch the specific assignment
            assignment = tbl_request_assignment.objects.get(assignmentID=aid)
            
            # 2. Update status to 'Completed' 
            # This is the final state after 'Accepted' and 'Delivered'
            assignment.assignment_status = 'Completed'
            assignment.save()

            # Volunteer becomes free only on completion confirmation.
            if assignment.volunteerID:
                assignment.volunteerID.availability_status = 'Available'
                assignment.volunteerID.save()
            
            messages.success(request, "Task officially confirmed and marked as Completed.")
        except tbl_request_assignment.DoesNotExist:
            messages.error(request, "Task not found.")
            
        return redirect('ngo_accepted_tasks')

def ngo_completed_history(request):
    ngo_id = request.session.get('ngo_id')
    
    # Base query for all completed tasks for this NGO
    # Exclude unverified community requests
    all_completed = tbl_request_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_status='Completed'
    ).exclude(
        request_serviceID__requestID__request_type='community',
        request_serviceID__requestID__campID__is_verified='No'
    ).select_related(
        'volunteerID', 
        'request_serviceID__requestID__affectedID',
        'request_serviceID__requestID__campID',
        'request_serviceID__serviceID'
    )

    # Split into two lists
    volunteer_tasks = [t for t in all_completed if t.volunteerID]
    internal_tasks = [t for t in all_completed if not t.volunteerID]

    context = {
        'volunteer_tasks': volunteer_tasks,
        'internal_tasks': internal_tasks
    }
    return render(request, 'ngo/completed_history.html', context)

def ngo_help_page(request):
    """Renders the page and provides the initial Category and Service lists."""
    categories = tbl_category.objects.all()
    service_types = tbl_service_type.objects.all()
    
    return render(request, 'ngo/ngo_add_items.html', {
        'categories': categories,
        'service_types': service_types
    })

def get_subcategories(request):
    category_id = request.GET.get('category_id')
    # Filter subcategories by the selected category
    subcategories = tbl_subcategory.objects.filter(categoryID_id=category_id)
    
    # Manually map to 'id' and 'name' so the JS can read it
    data = []
    for s in subcategories:
        data.append({
            'id': s.subCategoryId, 
            'name': s.SubCategoryname
        })
    
    return JsonResponse(data, safe=False)

def submit_help_details(request):
    if request.method == 'POST':
        ngo_id = request.session.get('ngo_id')
        
        # 1. Get the lists from the form
        categories = request.POST.getlist('category[]')
        subcategories = request.POST.getlist('subcategory[]')
        quantities = request.POST.getlist('quantity[]')

        for i in range(len(subcategories)):
            # Only process if a subcategory was selected
            if subcategories[i] and subcategories[i].strip():
                
                # 2. Check if this NGO already has a record for this item
                existing_item = tbl_ngo_helptype.objects.filter(
                    NGOID_id=ngo_id,
                    subCategoryID_id=subcategories[i]
                ).first()

                # Convert the new input quantity to an integer
                added_qty = int(quantities[i]) if quantities[i].isdigit() else 0

                if existing_item:
                    # 3. FIX: Add the new quantity to the existing quantity
                    # We convert to int to do math, then back to string for your CharField
                    current_qty = int(existing_item.quantity) if (existing_item.quantity and existing_item.quantity.isdigit()) else 0
                    existing_item.quantity = str(current_qty + added_qty)
                    existing_item.save()
                else:
                    # 4. If it's a new item for this NGO, create it normally
                    tbl_ngo_helptype.objects.create(
                        NGOID_id=ngo_id,
                        subCategoryID_id=subcategories[i],
                        categoryID_id=categories[i],
                        quantity=str(added_qty),
                        isActive='Yes'
                    )

        # Handling Non-Material Services (This part stays the same)
        services = request.POST.getlist('service_type[]')
        for service_id in services:
            if service_id and service_id.strip():
                tbl_ngo_helptype.objects.update_or_create(
                    NGOID_id=ngo_id,
                    serviceID_id=service_id,
                    defaults={'isActive': 'Yes'}
                )

        messages.success(request, "Stock updated successfully!")
        return redirect('/NGOapp/ngohome/')
    
    return redirect('/NGOapp/ngohome/')

# NGO Logout view
def ngo_logout(request):
    logout(request)
    request.session.flush()  # Clear all session data
    messages.success(request, 'You have been logged out successfully!')
    return redirect('login')

# NGO Profile view
def ngo_profile(request):
    ngo_id = request.session.get('ngo_id')
    if not ngo_id:
        messages.error(request, 'Please login to view your profile.')
        return redirect('login')
    
    ngo = tbl_ngo_reg.objects.select_related('TalukID', 'LocalbodyID', 'LoginID').get(NGOID=ngo_id)
    return render(request, 'ngo/profile.html', {'ngo': ngo})

# API endpoint to get community request details
def get_community_details(request, camp_id):
    """API endpoint to fetch full community request details"""
    try:
        from guestapp.models import tbl_community_request
        
        # Fetch community request with related location data
        community = tbl_community_request.objects.select_related(
            'talukID', 'localbodyID', 'wardID'
        ).get(campID=camp_id)
        
        # Fetch all requested items for this community
        request_obj = tbl_request.objects.filter(
            campID=community, 
            request_type='community'
        ).first()
        
        items = []
        if request_obj:
            request_services = tbl_request_service.objects.filter(
                requestID=request_obj
            ).select_related('categoryID', 'subCategoryID')
            
            for service in request_services:
                items.append({
                    'category': service.categoryID.CategoryName if service.categoryID else 'N/A',
                    'subcategory': service.subCategoryID.SubCategoryname if service.subCategoryID else 'N/A',
                    'quantity': service.quantity or 0,
                    'fulfilled': service.fulfilled_quantity or 0,
                    'status': service.status
                })
        
        # Prepare response data
        data = {
            'community_name': community.community_name or 'Unnamed Community',
            'coordinator_name': community.coordinator_name,
            'contact_number': community.contact_number,
            'address': community.address,
            'taluk': community.talukID.TalukName if community.talukID else 'N/A',
            'localbody': community.localbodyID.LocalbodyName if community.localbodyID else 'N/A',
            'ward': f"Ward {community.wardID.WardNumber}" if community.wardID else 'N/A',
            'estimated_people': community.estimated_people,
            'is_verified': community.is_verified,
            'items': items,
            'request_status': request_obj.request_status if request_obj else 'Unknown'
        }
        
        return JsonResponse(data, safe=False)
    except tbl_community_request.DoesNotExist:
        return JsonResponse({'error': 'Community request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)