from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import logout
from guestapp.models import tbl_request_assignment, tbl_volunteer_reg
# Create your views here.


def volunteer_dashboard(request):
    vol_id = request.session.get('vol_id')
    
    # Get the active task for this volunteer
    # We use .first() because a volunteer should ideally handle one task at a time
    current_task = tbl_request_assignment.objects.filter(
        volunteerID_id=vol_id,
        assignment_status='Accepted'
    ).select_related('request_serviceID__requestID__affectedID', 'request_serviceID__serviceID').first()

    return render(request, 'volunteer/index.html', {'task': current_task})

def update_work_status(request, aid):
    if request.method == "POST":
        assignment = tbl_request_assignment.objects.get(assignmentID=aid)
        
        # 1. Update status to 'Delivered' instead of 'Completed'
        assignment.assignment_status = 'Delivered'
        assignment.save()
        
        messages.success(request, "Delivery reported! Waiting for NGO to confirm.")
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