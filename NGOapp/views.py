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


def _deduct_stock_for_completed_assignment(assignment):
    """Reduce NGO stock once when an assignment is marked completed."""
    if not assignment or not assignment.NGOID_id or not assignment.request_serviceID:
        return False, "No assignment stock context found."

    req_service = assignment.request_serviceID
    stock_qs = tbl_ngo_helptype.objects.filter(
        NGOID_id=assignment.NGOID_id,
        isActive='Yes',
    )

    if req_service.subCategoryID_id:
        stock_qs = stock_qs.filter(subCategoryID_id=req_service.subCategoryID_id)
    elif req_service.serviceID_id:
        stock_qs = stock_qs.filter(serviceID_id=req_service.serviceID_id)
    else:
        return False, "No service/subcategory linked to assignment."

    stock_row = stock_qs.order_by('-quantity').first()
    if not stock_row:
        return False, "No matching NGO stock row found."

    try:
        current_qty = int(stock_row.quantity)
    except (TypeError, ValueError):
        current_qty = 0

    try:
        deduct_qty = int(assignment.assigned_quntity or 0)
    except (TypeError, ValueError):
        deduct_qty = 0

    if deduct_qty <= 0:
        try:
            deduct_qty = int(req_service.quantity or 1)
        except (TypeError, ValueError):
            deduct_qty = 1

    new_qty = max(current_qty - deduct_qty, 0)
    stock_row.quantity = str(new_qty)
    stock_row.save(update_fields=['quantity'])
    return True, f"Stock updated: -{deduct_qty}, remaining {new_qty}."


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


def _get_existing_request_volunteer(ngo_id, request_id):
    """Reuse already selected volunteer for the same NGO + request."""
    existing = (
        tbl_request_assignment.objects.filter(
            NGOID_id=ngo_id,
            request_serviceID__requestID_id=request_id,
            volunteerID__isnull=False,
        )
        .select_related('volunteerID')
        .order_by('assignmentID')
        .first()
    )
    return existing.volunteerID if existing else None


def _assign_volunteer_to_request_assignments(ngo_id, request_id, volunteer):
    """Keep a single volunteer mapped for all assignments of the same community request."""
    if not volunteer:
        return 0

    updated = (
        tbl_request_assignment.objects.filter(
            NGOID_id=ngo_id,
            request_serviceID__requestID_id=request_id,
        )
        .exclude(assignment_status='Completed')
        .update(volunteerID=volunteer)
    )
    return updated

def ngo_dashboard(request):
    ngo_id = request.session.get('ngo_id')
    
    # 1. PENDING REQUESTS (INDIVIDUAL + VERIFIED COMMUNITY)
    # This shows requests waiting for NGO to accept/reject
    pending_service_ids = tbl_request_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_status='Pending',
    ).exclude(
        request_serviceID__requestID__request_type='community',
        request_serviceID__requestID__campID__is_verified='No'
    ).values_list('request_serviceID_id', flat=True)

    pending_items = tbl_request_service.objects.filter(
        request_service_id__in=pending_service_ids,
    ).select_related(
        'requestID__affectedID',
        'requestID__affectedID__localbodyID',
        'requestID__affectedID__wardID',
        'requestID__campID',
        'requestID__campID__localbodyID',
        'requestID__campID__talukID',
        'serviceID',
        'subCategoryID',
    )
    
    # GROUP PENDING ITEMS BY REQUEST ID
    # For community requests with multiple items, group them into a single row
    from collections import OrderedDict
    
    grouped_pending = OrderedDict()
    for item in pending_items:
        req_id = item.requestID.request_id
        if req_id not in grouped_pending:
            # Initialize request group with metadata
            grouped_pending[req_id] = {
                'requestID': item.requestID,
                'request_type': item.requestID.request_type,
                'services': [],
            }
        # Add service/item to this request group
        grouped_pending[req_id]['services'].append(item)
    
    # Convert OrderedDict to list of grouped requests for template
    pending_assignments_grouped = list(grouped_pending.values())

    # 2. COMMUNITY TASKS LOGIC - Active community requests (Accepted/Delivered)
    # Only show verified community requests that are in progress
    community_tasks = tbl_request_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_status__in=['Accepted', 'Delivered'],
        request_serviceID__requestID__request_type='community',
        request_serviceID__requestID__campID__is_verified='Yes'
    ).select_related('request_serviceID__requestID__campID', 'request_serviceID__subCategoryID')

    # 3. RETRIEVE & CLEAR ACCUMULATED NOTIFICATIONS
    from guestapp.models import tbl_ngo_request_notification
    accumulated_notifications = tbl_ngo_request_notification.objects.filter(
        NGOID_id=ngo_id,
        response_status='Pending'
    ).select_related('requestID', 'requestID__campID', 'requestID__affectedID').order_by('-notified_at')
    
    # Mark old notifications (>5 minutes) as read to prevent accumulation
    from django.utils import timezone
    from datetime import timedelta
    cutoff_time = timezone.now() - timedelta(minutes=5)
    tbl_ngo_request_notification.objects.filter(
        NGOID_id=ngo_id,
        response_status='Pending',
        notified_at__lt=cutoff_time
    ).update(response_status='Read')
    
    # Fresh pending notifications (less than 5 minutes)
    notifications = accumulated_notifications.filter(notified_at__gte=cutoff_time)

    # 4. GLOBAL SAFETY BUFFER ALERTS (DATABASE-DRIVEN) - COMMENTED OUT
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

    # 5. DROPDOWN & STAT DATA
    context = {
        'pending_assignments': pending_assignments_grouped,
        'community_tasks': community_tasks,
        'notifications': notifications,
        'notification_count': notifications.count(),
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
        action = request.POST.get('action')
        is_community = request.POST.get('is_community', 'false').lower() == 'true'
        
        # Handle both single service ID (individual) and multiple service IDs (community)
        if is_community:
            service_ids_str = request.POST.get('service_ids', '')
            service_ids = [int(sid.strip()) for sid in service_ids_str.split(',') if sid.strip()]
            req_services = tbl_request_service.objects.filter(request_service_id__in=service_ids)
        else:
            req_service_id = request.POST.get('assignment_id')
            req_services = tbl_request_service.objects.filter(request_service_id=req_service_id)
        
        if not req_services.exists():
            messages.error(request, "Request service not found.")
            return redirect('/NGOapp/ngohome/')
        
        # Get the parent request (same for all services in a community request)
        parent_request = req_services.first().requestID
        
        if action == "reject":
            # Reject all service assignments for this request
            rejected_count = 0
            for req_service in req_services:
                assignment = tbl_request_assignment.objects.filter(
                    NGOID_id=ngo_id,
                    request_serviceID=req_service,
                ).first()
                
                if assignment:
                    assignment.assignment_status = 'Rejected by NGO'
                    assignment.save()
                    rejected_count += 1
            
            # Mark notification as rejected
            from guestapp.models import tbl_ngo_request_notification
            from django.utils import timezone
            tbl_ngo_request_notification.objects.filter(
                requestID=parent_request,
                NGOID_id=ngo_id
            ).update(response_status='Rejected', response_at=timezone.now())
            
            messages.info(request, f"Request rejected ({rejected_count} item(s)).")
            return redirect('/NGOapp/ngohome/')

        if action == "accept":
            # Check if any service is already accepted
            existing_accepted = tbl_request_assignment.objects.filter(
                NGOID_id=ngo_id,
                request_serviceID__in=req_services,
                assignment_status__in=['Accepted', 'Delivered', 'Completed']
            ).exists()
            
            if existing_accepted:
                messages.warning(request, "This request has already been accepted.")
                return redirect('/NGOapp/ngohome/')

            # Mark notification as accepted
            from guestapp.models import tbl_ngo_request_notification
            from django.utils import timezone
            tbl_ngo_request_notification.objects.filter(
                requestID=parent_request,
                NGOID_id=ngo_id
            ).update(response_status='Accepted', response_at=timezone.now())

            # 1. Update global request status and assignment state.
            parent_request.request_status = 'Approved'
            parent_request.NGOID_id = ngo_id
            parent_request.save()

            # Create/update assignments for all services
            assignments = []
            for req_service in req_services:
                assignment = tbl_request_assignment.objects.filter(
                    NGOID_id=ngo_id,
                    request_serviceID=req_service,
                ).first()

                if not assignment:
                    assignment = tbl_request_assignment.objects.create(
                        NGOID_id=ngo_id,
                        request_serviceID=req_service,
                        assigned_quntity=1,
                        assignment_status='Accepted',
                    )
                else:
                    assignment.assignment_status = 'Accepted'
                    assignment.assigned_quntity = assignment.assigned_quntity or 1
                    assignment.save()
                
                assignments.append(assignment)

            # 2. External volunteer auto-assignment: Primary first, then Emergency.
            ngo = tbl_ngo_reg.objects.get(NGOID=ngo_id)
            has_volunteer_raw = str(ngo.hasVolunteers or '').strip().lower()

            if has_volunteer_raw == 'no':
                selected_volunteer = None
                if parent_request.request_type == 'community':
                    # For community requests, try to reuse existing volunteer for this request
                    selected_volunteer = _get_existing_request_volunteer(ngo_id, parent_request.request_id)

                if not selected_volunteer:
                    # Pick an external volunteer if available
                    selected_volunteer = _pick_external_ngo_volunteer(ngo_id, assignments[0].assignmentID if assignments else None)

                if selected_volunteer:
                    # Assign volunteer to all assignments (for community requests)
                    for assignment in assignments:
                        assignment.volunteerID = selected_volunteer
                        assignment.assignment_status = 'Accepted'
                        assignment.save()

                    # If community request, propagate volunteer to all sibling assignments
                    if parent_request.request_type == 'community':
                        _assign_volunteer_to_request_assignments(
                            ngo_id,
                            parent_request.request_id,
                            selected_volunteer,
                        )

                    selected_volunteer.availability_status = 'Busy'
                    selected_volunteer.save()

                    # Send email notification to volunteer
                    if selected_volunteer.Email:
                        try:
                            subject = 'ResQLink Assignment Notification'
                            if parent_request.request_type == 'community' and parent_request.campID:
                                requester_label = f"Community: {parent_request.campID.community_name}"
                                service_list = ', '.join([
                                    (service.subCategoryID.SubCategoryname if service.subCategoryID else 
                                     service.serviceID.serviceName if service.serviceID else 'General Help')
                                    for service in req_services
                                ])
                            else:
                                req_service = req_services.first()
                                requester_label = f"Requester: {parent_request.affectedID.name if parent_request.affectedID else 'N/A'}"
                                service_list = (req_service.subCategoryID.SubCategoryname if req_service.subCategoryID else 
                                               req_service.serviceID.serviceName if req_service.serviceID else 'General Help')

                            message = (
                                f"Hello {selected_volunteer.Name},\n\n"
                                f"A new request has been assigned to you.\n"
                                f"{requester_label}\n"
                                f"Service: {service_list}\n"
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
                    for assignment in assignments:
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
        'request_serviceID__requestID__campID',
        'request_serviceID__requestID__affectedID',
        'volunteerID',
    )

    # GROUP ACCEPTED TASKS BY REQUEST ID
    # For community requests with multiple items, group them into a single row
    from collections import OrderedDict
    
    grouped_tasks = OrderedDict()
    for task in accepted_list:
        req_id = task.request_serviceID.requestID.request_id
        if req_id not in grouped_tasks:
            # Initialize request group with metadata
            grouped_tasks[req_id] = {
                'requestID': task.request_serviceID.requestID,
                'request_type': task.request_serviceID.requestID.request_type,
                'assignments': [],
                'volunteer': task.volunteerID,  # Use first volunteer (all should be same for community)
                'status': task.assignment_status,  # Use first status (all should be same for community)
            }
        # Add assignment to this request group
        grouped_tasks[req_id]['assignments'].append(task)
    
    # Convert OrderedDict to list of grouped requests for template
    accepted_tasks_grouped = list(grouped_tasks.values())
    
    # Add can_assign_waiting_volunteer flag to each grouped task
    for task_group in accepted_tasks_grouped:
        task_group['can_assign_waiting_volunteer'] = False
        if task_group['status'] == 'Waiting Admin Approval':
            # Check if any volunteer is available
            task_group['can_assign_waiting_volunteer'] = _pick_external_ngo_volunteer(
                ngo_id,
                task_group['assignments'][0].assignmentID,
            ) is not None

    return render(request, 'ngo/accepted_task.html', {'accepted_list': accepted_tasks_grouped})


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

    parent_request = assignment.request_serviceID.requestID

    selected_volunteer = None
    if parent_request.request_type == 'community':
        selected_volunteer = _get_existing_request_volunteer(ngo_id, parent_request.request_id)

    if not selected_volunteer:
        selected_volunteer = _pick_external_ngo_volunteer(ngo_id, assignment.assignmentID)

    if not selected_volunteer:
        messages.warning(request, 'No volunteers are free right now. Please try again shortly.')
        return redirect('ngo_accepted_tasks')

    assignment.volunteerID = selected_volunteer
    assignment.assignment_status = 'Accepted'
    assignment.save(update_fields=['volunteerID', 'assignment_status'])

    if parent_request.request_type == 'community':
        _assign_volunteer_to_request_assignments(
            ngo_id,
            parent_request.request_id,
            selected_volunteer,
        )

    selected_volunteer.availability_status = 'Busy'
    selected_volunteer.save(update_fields=['availability_status'])

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
            assignment = tbl_request_assignment.objects.select_related('request_serviceID__requestID').get(assignmentID=aid)

            if assignment.assignment_status == 'Completed':
                messages.info(request, "Task is already completed.")
                return redirect('ngo_accepted_tasks')

            stock_ok, stock_msg = _deduct_stock_for_completed_assignment(assignment)
            
            # 2. Update status to 'Completed' 
            # This is the final state after 'Accepted' and 'Delivered'
            assignment.assignment_status = 'Completed'
            assignment.save(update_fields=['assignment_status'])

            # Sync item-level progress for tracker table and admin views.
            request_service = assignment.request_serviceID
            service_assignments = tbl_request_assignment.objects.filter(
                request_serviceID=request_service
            )
            completed_assignments = service_assignments.filter(assignment_status='Completed')

            completed_qty = 0
            for qty in completed_assignments.values_list('assigned_quntity', flat=True):
                try:
                    completed_qty += int(qty or 0)
                except (TypeError, ValueError):
                    continue

            requested_qty = request_service.quantity
            if requested_qty is None:
                # Quantity is optional for service-type individual requests.
                request_service.status = 'Completed' if completed_assignments.exists() else 'Pending'
            else:
                try:
                    requested_qty_int = int(requested_qty)
                except (TypeError, ValueError):
                    requested_qty_int = 0

                if completed_qty >= requested_qty_int and requested_qty_int > 0:
                    request_service.status = 'Completed'
                elif completed_qty > 0:
                    request_service.status = 'In Progress'
                else:
                    request_service.status = 'Pending'

            request_service.fulfilled_quantity = completed_qty
            request_service.save(update_fields=['status', 'fulfilled_quantity'])

            # Keep parent request status in sync with aggregate assignment progress.
            parent_request = assignment.request_serviceID.requestID
            parent_assignments = tbl_request_assignment.objects.filter(
                request_serviceID__requestID=parent_request
            )
            assignment_states = list(parent_assignments.values_list('assignment_status', flat=True))
            if assignment_states and all(state == 'Completed' for state in assignment_states):
                parent_request.request_status = 'Completed'
                parent_request.save(update_fields=['request_status'])

            # Volunteer becomes free only on completion confirmation.
            if assignment.volunteerID:
                assignment.volunteerID.availability_status = 'Available'
                assignment.volunteerID.save()
            
            if stock_ok:
                messages.success(request, f"Task officially confirmed and marked as Completed. {stock_msg}")
            else:
                messages.warning(request, f"Task completed, but stock update skipped. {stock_msg}")
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