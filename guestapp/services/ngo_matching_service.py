from guestapp.models import tbl_ngo_reg, tbl_request_service, tbl_request, tbl_request_assignment
from NGOapp.models import tbl_ngo_helptype
from django.core.mail import send_mail
from django.conf import settings

# Import your detailed template
from .email_service import notify_ngos 

def find_and_notify_ngos(request_obj):
    # Get all services requested in this specific request
    request_services = tbl_request_service.objects.filter(requestID=request_obj)
    
    # Determine location based on request type
    if request_obj.request_type == 'individual':
        location_localbody = request_obj.affectedID.localbodyID if request_obj.affectedID else None
        location_taluk = request_obj.affectedID.talukID if request_obj.affectedID else None
    else:  # community request
        location_localbody = request_obj.campID.localbodyID if request_obj.campID else None
        location_taluk = request_obj.campID.talukID if request_obj.campID else None
    
    eligible_ngos = [] # This will store NGO registration objects
    seen_ngo_ids = set()
    ngo_emails = set() # This ensures we don't send duplicate emails to the same NGO
    
    for rs in request_services:
        # STEP 1: Search by Localbody (Hyper-local)
        ngos = tbl_ngo_helptype.objects.filter(
            serviceID=rs.serviceID,
            isActive='Yes',
            NGOID__LocalbodyID=location_localbody,
            NGOID__LoginID__Status='Approved'
        ).select_related('NGOID')
        
        # STEP 2: If no one in Localbody, expand search to the whole Taluk
        if not ngos.exists():
            ngos = tbl_ngo_helptype.objects.filter(
                serviceID=rs.serviceID,
                isActive='Yes',
                NGOID__TalukID=location_taluk,
                NGOID__LoginID__Status='Approved'
            ).select_related('NGOID')
        
        # STEP 3: If no one in Taluk and it's an individual request, search outside taluk
        if not ngos.exists() and request_obj.request_type == 'individual':
            ngos = tbl_ngo_helptype.objects.filter(
                serviceID=rs.serviceID,
                isActive='Yes',
                NGOID__LoginID__Status='Approved'
            ).exclude(
                NGOID__TalukID=location_taluk
            ).select_related('NGOID')

        # Collect unique NGOs and their emails
        for ngo_stock in ngos:
            ngo_obj = ngo_stock.NGOID
            if ngo_obj.Email:
                ngo_emails.add(ngo_obj.Email)
            
            # Add to list if not already present to avoid duplicates
            if ngo_obj.NGOID not in seen_ngo_ids:
                seen_ngo_ids.add(ngo_obj.NGOID)
                eligible_ngos.append(ngo_obj)

    # EMERGENCY FALLBACK: if no exact service match, alert approved NGOs by location
    if not eligible_ngos:
        emergency_ngos = tbl_ngo_reg.objects.filter(
            LoginID__Status='Approved',
            LocalbodyID=location_localbody
        )

        if not emergency_ngos.exists() and location_taluk:
            emergency_ngos = tbl_ngo_reg.objects.filter(
                LoginID__Status='Approved',
                TalukID=location_taluk
            )

        if not emergency_ngos.exists():
            emergency_ngos = tbl_ngo_reg.objects.filter(LoginID__Status='Approved')

        for ngo_obj in emergency_ngos:
            if ngo_obj.NGOID not in seen_ngo_ids:
                seen_ngo_ids.add(ngo_obj.NGOID)
                eligible_ngos.append(ngo_obj)
            if ngo_obj.Email:
                ngo_emails.add(ngo_obj.Email)

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
