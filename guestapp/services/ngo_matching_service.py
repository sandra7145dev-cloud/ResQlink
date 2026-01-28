from guestapp.models import tbl_ngo_reg, tbl_request_service, tbl_request, tbl_request_assignment
from NGOapp.models import tbl_ngo_helptype
from django.core.mail import send_mail
from django.conf import settings

# Import your detailed template
from .email_service import notify_ngos 

def find_and_notify_ngos(request_obj):
    # Get all services requested in this specific request
    request_services = tbl_request_service.objects.filter(requestID=request_obj)
    affected_individual = request_obj.affectedID
    
    eligible_ngos = [] # This will store the actual NGO objects
    ngo_emails = set() # This ensures we don't send duplicate emails to the same NGO
    
    for rs in request_services:
        # STEP 1: Search by Localbody (Hyper-local)
        ngos = tbl_ngo_helptype.objects.filter(
            serviceID=rs.serviceID,
            isActive='Yes',
            NGOID__LocalbodyID=affected_individual.localbodyID 
        ).select_related('NGOID')
        
        # STEP 2: If no one in Localbody, expand search to the whole Taluk
        if not ngos.exists():
            ngos = tbl_ngo_helptype.objects.filter(
                serviceID=rs.serviceID,
                isActive='Yes',
                NGOID__TalukID=affected_individual.talukID 
            ).select_related('NGOID')

        # Collect unique NGOs and their emails
        for ngo in ngos:
            if ngo.NGOID.Email:
                ngo_emails.add(ngo.NGOID.Email)
            
            # Add to list if not already present to avoid duplicates
            if ngo not in eligible_ngos:
                eligible_ngos.append(ngo)

    # STEP 3: Trigger the email template notification
    if ngo_emails:
        try:
            # list(ngo_emails) converts the set to a list for the mail function
            notify_ngos(list(ngo_emails), request_obj)
        except Exception as e:
            # Prints error to terminal if email fails (useful for debugging)
            print(f"Error sending notification emails: {e}")
    
    return eligible_ngos

def assign_request_to_ngos(request_obj, ngo_list):
    """
    Inserts data into tbl_request_assignment with status 'Pending'.
    """
    request_services = tbl_request_service.objects.filter(requestID=request_obj)
    for rs in request_services:
        for ngo in ngo_list:
            # Check if this assignment already exists to prevent duplicates
            exists = tbl_request_assignment.objects.filter(
                request_serviceID=rs,
                NGOID=ngo
            ).exists()
            
            if not exists:
                tbl_request_assignment.objects.create(
                    request_serviceID=rs,
                    NGOID=ngo,
                    assignment_status='Pending'
                )
                print(f"--- DEBUG: Created Pending Assignment for NGO: {ngo.NGOname} ---")
