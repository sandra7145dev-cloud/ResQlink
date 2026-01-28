from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse
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

def update_work_status(request, assignment_id):
    if request.method == "POST":
        # 1. Update the Assignment Status
        assignment = tbl_request_assignment.objects.get(assignmentID=assignment_id)
        assignment.assignment_status = 'Completed'
        assignment.save()

        # 2. Update the Volunteer Availability
        volunteer = assignment.volunteerID
        volunteer.availability_status = 'Available'
        volunteer.save()

        # 3. Update the Parent Request Status (Optional: if all services for that request are done)
        # For now, we'll just mark this specific assignment as finished
        
        messages.success(request, "Great job! Task marked as completed. You are now available for new assignments.")
        return redirect('volunteer_dashboard')