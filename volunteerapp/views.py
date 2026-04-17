from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import logout
from guestapp.models import tbl_request_assignment, tbl_volunteer_reg
# Create your views here.


def volunteer_dashboard(request):
    vol_id = request.session.get('vol_id')
    
    # Get all active tasks for this volunteer
    active_assignments = tbl_request_assignment.objects.filter(
        volunteerID_id=vol_id,
        assignment_status='Accepted'
    ).select_related(
        'request_serviceID__requestID__affectedID',
        'request_serviceID__requestID__campID',
        'request_serviceID__serviceID',
        'request_serviceID__subCategoryID',
    )

    # GROUP ACTIVE TASKS BY REQUEST ID
    # For community requests with multiple items, group them into a single task card
    from collections import OrderedDict
    
    grouped_tasks = OrderedDict()
    for assignment in active_assignments:
        req_id = assignment.request_serviceID.requestID.request_id
        if req_id not in grouped_tasks:
            # Initialize request group with metadata
            grouped_tasks[req_id] = {
                'requestID': assignment.request_serviceID.requestID,
                'request_type': assignment.request_serviceID.requestID.request_type,
                'assignments': [],
            }
        # Add assignment to this request group
        grouped_tasks[req_id]['assignments'].append(assignment)
    
    # Convert OrderedDict to list of grouped requests for template
    active_tasks_grouped = list(grouped_tasks.values())

    return render(request, 'volunteer/index.html', {'tasks': active_tasks_grouped})

def update_work_status(request, aid):
    if request.method == "POST":
        assignment = tbl_request_assignment.objects.get(assignmentID=aid)
        
        # Get the parent request to find all related assignments
        parent_request = assignment.request_serviceID.requestID
        
        # Mark all assignments for this request as 'Delivered'
        # This ensures all items in a community request are marked together
        all_assignments = tbl_request_assignment.objects.filter(
            request_serviceID__requestID=parent_request,
            volunteerID_id=assignment.volunteerID_id,
            assignment_status='Accepted'
        )
        
        updated_count = all_assignments.update(assignment_status='Delivered')
        
        messages.success(request, f"Delivery reported! {updated_count} item(s) marked as delivered. Waiting for NGO to confirm.")
    return redirect('volunteer_dashboard')

# Volunteer Logout view
def volunteer_logout(request):
    logout(request)
    request.session.flush()  # Clear all session data
    messages.success(request, 'You have been logged out successfully!')
    return redirect('login')

# Volunteer Profile view
def volunteer_profile(request):
    vol_id = request.session.get('vol_id')
    if not vol_id:
        messages.error(request, 'Please login to view your profile.')
        return redirect('login')
    
    volunteer = tbl_volunteer_reg.objects.select_related('TalukID', 'LocalbodyID', 'LoginId').get(VolunteerId=vol_id)
    return render(request, 'volunteer/profile.html', {'volunteer': volunteer})