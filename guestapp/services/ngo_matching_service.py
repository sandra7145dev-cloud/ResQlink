from guestapp.models import tbl_ngo_reg, tbl_request_service, tbl_request, tbl_request_assignment
from NGOapp.models import tbl_ngo_helptype
from django.core.mail import send_mail
from django.conf import settings

def find_and_notify_ngos(request_obj):
    request_services = tbl_request_service.objects.filter(requestID=request_obj)
    affected_individual = request_obj.affectedID
    
    eligible_ngos = set()
    
    for rs in request_services:
        ngos = tbl_ngo_helptype.objects.filter(
            serviceID=rs.serviceID,
            isActive='Yes',
            NGOID__LocalbodyID=affected_individual.localbodyID  # Match NGOs in the same localbody
        )
        for ngo in ngos:
            eligible_ngos.add(ngo)  # Add to set
            # Send email for each service immediately
            send_mail(
                subject=f"Emergency Request: {rs.serviceID}",
                message=f"Emergency request in {affected_individual.localbodyID.LocalbodyName}. Contact: {affected_individual.contact_number}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[ngo.NGOID.Email],  # Use NGO's registered email
                fail_silently=False,
            )
    
    return list(eligible_ngos)

def assign_request_to_ngos(request_obj, ngo_list):
    request_services = tbl_request_service.objects.filter(requestID=request_obj)
    for rs in request_services:
        for ngo in ngo_list:
            tbl_request_assignment.objects.create(
                request_serviceID=rs,
                NGOID=ngo.NGOID,
                assignment_status='Pending'  # Initially pending
            )

