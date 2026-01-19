# guestapp/services/email_service.py
from django.core.mail import send_mail
from django.conf import settings

def notify_ngos(ngo_emails, help_request):
    """
    Send email notifications to a list of NGOs about a new help request.
    """

    subject = "EMERGENCY | Individual Help Request"

    # ---------- INDIVIDUAL REQUEST ----------
    if help_request.request_type == 'individual':

        # Fetch requested services (Food, Water, etc.)
        services = help_request.request_services.all()  # related_name assumed
        if services:
            required_help = ", ".join(
                f"{s.serviceID.service_name} ({s.quantity})"
                for s in services
            )
        else:
            required_help = "Not specified"

        body = f"""
Emergency Help Request (Individual)

Disaster: {help_request.disasterID.DisasterName if help_request.disasterID else 'N/A'}

Location:
{help_request.affectedID.localbody if help_request.affectedID else 'N/A'},
Ward {help_request.affectedID.ward if help_request.affectedID else 'N/A'}

Required Help:
{required_help}

Contact:
{help_request.affectedID.contact_number if help_request.affectedID else 'N/A'}

Request ID:
{help_request.request_id}

Please respond immediately if you can assist.
        """

    # ---------- COMMUNITY REQUEST ----------
    elif help_request.request_type == 'community':
        subject = "Community Help Request"

        body = f"""
Community Help Request

Request ID: {help_request.request_id}
Community Name: {help_request.campID.community_name if help_request.campID else 'N/A'}
Coordinator: {help_request.campID.coordinator_name if help_request.campID else 'N/A'}
Estimated People: {help_request.campID.estimated_people if help_request.campID else 'N/A'}
Address: {help_request.campID.address if help_request.campID else 'N/A'}

Please respond as soon as possible.
        """

    else:
        body = "New help request submitted."

    # ---------- SEND EMAIL ----------
    for email in ngo_emails:
        send_mail(
            subject,
            body.strip(),
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
