from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from adminapp.models import tbl_category, tbl_subcategory, tbl_service_type
from guestapp.models import tbl_ngo_reg, tbl_request, tbl_request_assignment, tbl_request_service, tbl_volunteer_reg
from .models import tbl_ngo_helptype
from django.core.mail import send_mail
import random

# Create your views here.


def ngo_dashboard(request):
    ngo_id = request.session.get('ngo_id')
    print(f"--- DEBUG: Logged in NGO ID is: {ngo_id} ---")
    
    # 1. Get the list of Service IDs this NGO provides
    provided_service_ids = tbl_ngo_helptype.objects.filter(
        NGOID_id=ngo_id, 
        isActive='Yes'
    ).values_list('serviceID_id', flat=True)

    # 2. Find Pending individual requests that need those specific services
    # We query tbl_request_service because that's where the specific service is linked
    pending_items = tbl_request_service.objects.filter(
        requestID__request_status='Pending',
        requestID__request_type='individual',
        serviceID_id__in=provided_service_ids
    ).select_related('requestID__affectedID', 'serviceID', 'requestID__affectedID__localbodyID', 'requestID__affectedID__wardID')

    context = {
        'pending_assignments': pending_items, # We keep the name so your HTML still works
    }
    
    return render(request, 'ngo/index.html', context)

def ngo_accept_reject_request(request):
    if request.method == "POST":
        ngo_id = request.session.get('ngo_id')
        req_service_id = request.POST.get('assignment_id') 
        action = request.POST.get('action')
        
        req_service = tbl_request_service.objects.get(request_service_id=req_service_id)
        parent_request = req_service.requestID

        if action == "accept":
            print(f"--- DEBUG: Action is ACCEPT for NGO ID: {ngo_id} ---")
            # 1. Prevent double-acceptance
            if parent_request.request_status == 'Approved':
                messages.warning(request, "This request has already been accepted.")
                return redirect('/NGOapp/ngohome/')

            # 2. Update Global Request Status
            parent_request.request_status = 'Approved'
            parent_request.NGOID_id = ngo_id
            parent_request.save()

            # 3. Create the Assignment Record
            assignment = tbl_request_assignment.objects.create(
                NGOID_id=ngo_id,
                request_serviceID=req_service,
                assigned_quntity=1,
                assignment_status='Accepted'
            )

            # 4. SMART AUTO-VOLUNTEER ASSIGNMENT LOGIC
            ngo = tbl_ngo_reg.objects.get(NGOID=ngo_id)
            
            # Clean the input to ensure comparison works 100%
            has_no_staff = str(ngo.hasVolunteers).strip() == 'No'
            
            print(f"--- CRITICAL DEBUG: NGO '{ngo.NGOname}' | Value: '{ngo.hasVolunteers}' | Match 'No': {has_no_staff} ---")
            
            if has_no_staff:
                print("--- STATUS: Starting search for External Volunteers ---")
                
                # STEP A: Find ALL eligible volunteers in the EXACT same Local Body
                eligible_volunteers = tbl_volunteer_reg.objects.filter(
                    LocalbodyID=parent_request.affectedID.localbodyID,
                    availability_status='Available',
                    LoginId__Status='Approved'
                )
                print(f"--- DEBUG STEP A: Local Body Match Count: {eligible_volunteers.count()} ---")

                # STEP B: If no one in Local Body, find ALL in the whole Taluk
                if not eligible_volunteers.exists():
                    print("--- DEBUG: Local Body empty. Trying Taluk fallback... ---")
                    eligible_volunteers = tbl_volunteer_reg.objects.filter(
                        TalukID=parent_request.affectedID.talukID,
                        availability_status='Available',
                        LoginId__Status='Approved'
                    )
                    print(f"--- DEBUG STEP B: Taluk Match Count: {eligible_volunteers.count()} ---")

                # STEP C: Pick ONE random volunteer from the eligible list
                if eligible_volunteers.exists():
                    assigned_volunteer = random.choice(list(eligible_volunteers))
                    print(f"--- SUCCESS: Selected Volunteer {assigned_volunteer.Name} ---")
                    
                    # Update assignment with the found volunteer
                    assignment.volunteerID = assigned_volunteer
                    assignment.save()

                    # Mark volunteer as 'Busy'
                    assigned_volunteer.availability_status = 'Busy'
                    assigned_volunteer.save()

                    # --- EMAIL NOTIFICATION LOGIC ---
                    try:
                        subject = 'Urgent: ResQLink Emergency Assignment'
                        message = (
                            f"Hello {assigned_volunteer.Name},\n\n"
                            f"You have been assigned to help {parent_request.affectedID.name}.\n"
                            f"Service Required: {req_service.serviceID.serviceName}\n"
                            f"Location: {parent_request.affectedID.address}\n\n"
                            f"Please log in to your ResQLink dashboard to view details."
                        )
                        send_mail(
                            subject, 
                            message, 
                            'sandra7145dev@gmail.com', 
                            [assigned_volunteer.Email], 
                            fail_silently=False
                        )
                        print(f"--- EMAIL: Sent successfully to {assigned_volunteer.Email} ---")
                    except Exception as e:
                        print(f"--- EMAIL ERROR: {e} ---")
                    
                    messages.success(request, f"Accepted! Volunteer {assigned_volunteer.Name} auto-assigned.")
                else:
                    print("--- FAILURE: No volunteers met criteria in LB or Taluk ---")
                    messages.warning(request, "Accepted, but no available volunteers found in your area.")
            else:
                print("--- STATUS: Skipping to Internal Staff block ---")
                messages.success(request, "Request accepted. Using NGO internal volunteers.")

        return redirect('/NGOapp/ngohome/')
    
def ngo_accepted_tasks(request):
    ngo_id = request.session.get('ngo_id')
    
    # We change assignment_status='Accepted' to assignment_status__in=['Accepted', 'Completed']
    accepted_list = tbl_request_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_status__in=['Accepted', 'Completed'] 
    ).select_related(
        'request_serviceID__requestID__affectedID', 
        'request_serviceID__serviceID',
        'volunteerID'
    ).order_by('-assignment_status') # This puts 'In Progress' at the top and 'Completed' at the bottom

    return render(request, 'ngo/accepted_task.html', {'accepted_list': accepted_list})

def ngo_complete_task(request, aid):
    if request.method == "POST":
        assignment = tbl_request_assignment.objects.get(assignmentID=aid)
        assignment.assignment_status = 'Completed'
        assignment.save()
        
        messages.success(request, "Task status updated to Completed.")
        return redirect('ngo_accepted_tasks')

def ngo_completed_history(request):
    ngo_id = request.session.get('ngo_id')
    
    # Base query for all completed tasks for this NGO
    all_completed = tbl_request_assignment.objects.filter(
        NGOID_id=ngo_id,
        assignment_status='Completed'
    ).select_related('volunteerID', 'request_serviceID__requestID__affectedID', 'request_serviceID__serviceID')

    # Split into two lists
    volunteer_tasks = [t for t in all_completed if t.volunteerID]
    internal_tasks = [t for t in all_completed if not t.volunteerID]

    context = {
        'volunteer_tasks': volunteer_tasks,
        'internal_tasks': internal_tasks
    }
    return render(request, 'ngo/completed_history.html', context)