from django.core.mail import send_mail
from django.conf import settings
from guestapp.models import tbl_request_service

def notify_ngos(ngo_emails, help_request):
    """
    Send email notifications to a list of NGOs about a new help request.
    """
    subject = "EMERGENCY | Individual Help Request"

    # ---------- INDIVIDUAL REQUEST ----------
    if help_request.request_type == 'individual':
        # Use the correct model for services
        services = tbl_request_service.objects.filter(requestID=help_request)
        
        if services.exists():
            required_help = "\n ".join(
                f"- {s.serviceID.serviceName} ({s.quantity})"
                for s in services
            )
        else:
            required_help = "Not specified"

        location = "N/A"
        contact = "N/A"
        
        if help_request.affectedID:
            # Matches your adminapp.tbl_ward field 'WardNumber'
            loc_name = help_request.affectedID.localbodyID.LocalbodyName
            ward_no = help_request.affectedID.wardID.WardNumber 
            
            location = f"{loc_name}, Ward {ward_no}"
            contact = help_request.affectedID.contact_number

        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        logic_link = f"{site_url}/guestapp/login/"

        body = f"""
Emergency Help Request (Individual)

Disaster: {help_request.disasterID.DisasterName if help_request.disasterID else 'N/A'}

Location:
{location}

Required Help:
{required_help}

Contact:
{contact}

Request ID:
{help_request.request_id}

To review and respond to this request, please log in to your NGO dashboard:
{logic_link}

Please respond immediately if you can assist.
        """

    # ---------- COMMUNITY REQUEST ----------
    elif help_request.request_type == 'community':
        subject = "Community Help Request"
        body = f"A new community request (ID: {help_request.request_id}) has been submitted. Please check the dashboard."

    else:
        body = "New help request submitted."

    # ---------- SEND EMAIL ----------
    for email in ngo_emails:
        try:
            send_mail(
                subject,
                message=body.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            print(f"--- SUCCESS: Email sent to {email} ---")
        except Exception as e:
            print(f"--- ERROR: Could not send email to {email}: {e} ---")