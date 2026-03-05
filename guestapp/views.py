from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from adminapp.models import tbl_taluk, tbl_localbody, tbl_disaster, tbl_ward, tbl_service_type, tbl_category, tbl_subcategory
from .models import (
    tbl_login,
    tbl_ngo_reg,
    tbl_volunteer_reg,
    tbl_affected_individual,
    tbl_community_request,
    tbl_request,
    tbl_request_service,
)
# Create your views here.# Add the second function name here so the Chef (view) can find the tool (function)
from .services.ngo_matching_service import find_and_notify_ngos, assign_request_to_ngos

def guesthome(request):
    taluks = tbl_taluk.objects.all()
    localbodies = tbl_localbody.objects.all()
    wards = tbl_ward.objects.all()
    disasters = tbl_disaster.objects.all()
    service_types = tbl_service_type.objects.all()
    categories = tbl_category.objects.all()
    subcategories = tbl_subcategory.objects.all()

    success = None
    error = None

    if request.method == 'POST':
        try:
            request_type = request.POST.get('request_type', 'individual')
            contact_number = request.POST.get('contact_number')
            address = request.POST.get('address')
            taluk_id = request.POST.get('taluk')
            localbody_id = request.POST.get('localbody')
            ward_id = request.POST.get('ward')

            # Get Taluk, Local Body, and Ward objects
            taluk = tbl_taluk.objects.get(TalukID=taluk_id)
            localbody = tbl_localbody.objects.get(LocalbodyID=localbody_id)
            ward = tbl_ward.objects.get(WardID=ward_id)
            
            # Get disaster and service type
            disaster_type_id = request.POST.get('disaster_type')
            service_type_id = request.POST.get('service_type')
            disaster = tbl_disaster.objects.get(DisasterID=disaster_type_id) if disaster_type_id else None
            service_type = tbl_service_type.objects.get(serviceID=service_type_id) if service_type_id else None

            if request_type == 'individual':
                # Handle individual request
                name = request.POST.get('name')
                age = request.POST.get('age')
                gender = request.POST.get('gender')

                if not all([name, age, gender, contact_number, address, taluk_id, localbody_id, ward_id, disaster_type_id, service_type_id]):
                    error = 'Please fill in all required fields.'
                else:
                    # Create affected individual record
                    affected_individual = tbl_affected_individual.objects.create(
                        name=name,
                        age=age,
                        gender=gender,
                        contact_number=contact_number,
                        address=address,
                        talukID=taluk,
                        localbodyID=localbody,
                        wardID=ward,
                    )
                    
                    # Create request record
                    help_request = tbl_request.objects.create(
                        request_type='individual',
                        affectedID=affected_individual,
                        disasterID=disaster,
                        request_status='Pending'
                    )
                    
                    # Create request service record
                    tbl_request_service.objects.create(
                        requestID=help_request,
                        serviceID=service_type,
                        quantity=None,
                        status='Pending'
                    )

                    # Individual requests are routed by admin approval workflow.
                    success = 'Request submitted successfully. It is now in admin review queue.'

            elif request_type == 'community':
                # Handle community request
                community_name = request.POST.get('community_name')
                coordinator_name = request.POST.get('coordinator_name')
                estimated_people = request.POST.get('estimated_people')
                categories = request.POST.getlist('category')
                subcategories = request.POST.getlist('subcategory')
                quantities_raw = request.POST.getlist('quantity')

                if not all([community_name, coordinator_name, estimated_people, contact_number, address, taluk_id, localbody_id, ward_id]):
                    error = 'Please fill in all required fields for community request.'
                elif not (len(categories) == len(subcategories) == len(quantities_raw)):
                    error = 'Each item must include a category, subcategory, and quantity.'
                else:
                    items = []
                    for category_id, subcategory_id, quantity in zip(categories, subcategories, quantities_raw):
                        if not all([category_id, subcategory_id, quantity]):
                            error = 'Each item must include a category, subcategory, and quantity.'
                            break
                        items.append((category_id, subcategory_id, quantity))

                    if not error:
                        if len(items) == 0:
                            error = 'Please add at least one item for community request.'
                        elif len(items) > 4:
                            error = 'You can add up to 4 items per community request.'
                        else:
                            parsed_quantities = []
                            try:
                                for _, _, quantity in items:
                                    qty_int = int(quantity)
                                    if qty_int <= 0:
                                        raise ValueError
                                    parsed_quantities.append(qty_int)
                            except ValueError:
                                error = 'Quantities must be whole numbers above zero.'

                        if not error:
                            community_req = tbl_community_request.objects.create(
                                community_name=community_name,
                                coordinator_name=coordinator_name,
                                estimated_people=int(estimated_people),
                                contact_number=contact_number,
                                address=address,
                                talukID=taluk,
                                localbodyID=localbody,
                                wardID=ward,
                                is_verified='No',
                            )

                            help_request = tbl_request.objects.create(
                                request_type='community',
                                campID=community_req,
                                disasterID=None,
                                request_status='Pending'
                            )

                            for (category_id, subcategory_id, _), quantity in zip(items, parsed_quantities):
                                category = tbl_category.objects.get(CategoryID=category_id)
                                subcategory = tbl_subcategory.objects.get(subCategoryId=subcategory_id)
                                tbl_request_service.objects.create(
                                    requestID=help_request,
                                    serviceID=None,
                                    categoryID=category,
                                    subCategoryID=subcategory,
                                    quantity=quantity,
                                    status='Pending'
                                )

                            # Don't notify NGOs for community requests - admin will handle verification and assignment
                            # eligible_ngos = find_and_notify_ngos(help_request)
                            # assign_request_to_ngos(help_request, eligible_ngos)

                            success = 'Community request submitted successfully. It will be reviewed by admin for verification.'

        except (tbl_taluk.DoesNotExist, tbl_localbody.DoesNotExist, tbl_ward.DoesNotExist, tbl_category.DoesNotExist, tbl_subcategory.DoesNotExist):
            error = 'Selected location, category, or subcategory was not found.'
        except ValueError:
            error = 'Invalid data format. Please check your inputs.'
        except Exception as exc:
            error = f'Unable to submit request: {exc}'

    return render(
        request,
        'guest/index.html',
        {
            'taluks': taluks,
            'localbodies': localbodies,
            'wards': wards,
            'disasters': disasters,
            'service_types': service_types,
            'categories': categories,
            'subcategories': subcategories,
            'success': success,
            'error': error,
        },
    )


def ngo_vol_sel(request):
    return render(request, 'guest/ngo_vol_sel.html')

def ngo_reg(request):
    taluks = tbl_taluk.objects.all()
    localbodies = tbl_localbody.objects.all()
    
    if request.method == 'POST':
        try:
            ngo_name = request.POST.get('ngo_name')
            reg_number = request.POST.get('reg_number')
            proof_document = request.FILES.get('proof_document')
            taluk_id = request.POST.get('taluk')
            localbody_id = request.POST.get('localbody')
            address = request.POST.get('address')
            contact_number1 = request.POST.get('phone')
            contact_number2 = request.POST.get('phone_other')
            email = request.POST.get('email')
            has_volunteers = request.POST.get('has_volunteers', 'No')
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            # Validate required fields
            if not all([ngo_name, reg_number, proof_document, taluk_id, localbody_id, address, contact_number1, email, username, password]):
                return render(request, 'guest/ngo_reg.html', {
                    'taluks': taluks,
                    'localbodies': localbodies,
                    'error': 'All fields are required.'
                })
            
            # Get Taluk and Local Body objects
            taluk = tbl_taluk.objects.get(TalukID=taluk_id)
            localbody = tbl_localbody.objects.get(LocalbodyID=localbody_id)
            
            # Check if username already exists
            if tbl_login.objects.filter(Username=username).exists():
                return render(request, 'guest/ngo_reg.html', {
                    'taluks': taluks,
                    'localbodies': localbodies,
                    'error': 'Username already exists. Please choose a different username.'
                })
            
            # Create login entry
            login = tbl_login.objects.create(
                Username=username,
                Password=password,
                Role='NGO',
                Status='Pending'
            )
            
            # Create NGO registration entry
            ngo_registration = tbl_ngo_reg.objects.create(
                LoginID=login,
                NGOname=ngo_name,
                RegNumber=reg_number,
                TalukID=taluk,
                LocalbodyID=localbody,
                Address=address,
                ContactNumber1=contact_number1,
                ContactNumber2=contact_number2 if contact_number2 else '',
                Email=email,
                ProofDocument=proof_document,
                hasVolunteers=has_volunteers
            )
            
            return render(request, 'guest/ngo_reg.html', {
                'taluks': taluks,
                'localbodies': localbodies,
                'success': 'Registration successful! Your NGO has been registered. Please login with your credentials.'
            })
            
        except tbl_taluk.DoesNotExist:
            return render(request, 'guest/ngo_reg.html', {
                'taluks': taluks,
                'localbodies': localbodies,
                'error': 'Selected Taluk does not exist.'
            })
        except tbl_localbody.DoesNotExist:
            return render(request, 'guest/ngo_reg.html', {
                'taluks': taluks,
                'localbodies': localbodies,
                'error': 'Selected Local Body does not exist.'
            })
        except Exception as e:
            return render(request, 'guest/ngo_reg.html', {
                'taluks': taluks,
                'localbodies': localbodies,
                'error': f'Registration failed: {str(e)}'
            })
    
    return render(request, 'guest/ngo_reg.html', {'taluks': taluks, 'localbodies': localbodies})
    
    

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if tbl_login.objects.filter(Username=username, Password=password).exists():
            log = tbl_login.objects.filter(Username=username, Password=password).first()
            request.session['LoginID'] = log.LoginID
            role = log.Role
            status = log.Status
            
            if role == 'ADMIN':
                return redirect('/adminapp/adminhome/')
            elif role == 'NGO':
                if status == 'Approved':
                    ngo_data = tbl_ngo_reg.objects.filter(LoginID=log).first()
                    if ngo_data:
                        request.session['ngo_id'] = ngo_data.NGOID
                        request.session['ngo_name'] = ngo_data.NGOname
                    return redirect('/NGOapp/ngohome/')
                else:
                    return render(request, 'guest/login.html', {
                        'error': 'Your NGO account is not verified yet. Please wait for admin approval.'
                    })
            elif role == 'VOLUNTEER':
                if status == 'Approved':
                    vol_data = tbl_volunteer_reg.objects.filter(LoginId=log).first()
                    if vol_data:
                        request.session['vol_id'] = vol_data.VolunteerId
                        request.session['vol_name'] = vol_data.Name
                    return redirect('/volunteerapp/volunteer_dashboard/')
                else:
                    return render(request, 'guest/login.html', {
                        'error': 'Your volunteer account is not verified yet. Please wait for admin approval.'
                    })
            else:
                return render(request, 'guest/login.html', {
                    'error': 'Invalid role. Please contact administrator.'
                })
        else:
            return render(request, 'guest/login.html', {
                'error': 'Invalid username or password'
            })
    else:
        return render(request, 'guest/login.html')


def _get_recovery_email(login_obj):
    if login_obj.Role == 'NGO':
        ngo_data = tbl_ngo_reg.objects.filter(LoginID=login_obj).first()
        return ngo_data.Email if ngo_data else None

    if login_obj.Role == 'VOLUNTEER':
        volunteer_data = tbl_volunteer_reg.objects.filter(LoginId=login_obj).first()
        return volunteer_data.Email if volunteer_data else None

    return None


def forgot_password(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()

        if not username:
            return render(request, 'guest/forgot_password.html', {
                'error': 'Please enter your username.'
            })

        login_obj = tbl_login.objects.filter(Username=username).first()

        if not login_obj:
            return render(request, 'guest/forgot_password.html', {
                'success': 'If the account exists, a password reset link has been sent to the registered email.'
            })

        recovery_email = _get_recovery_email(login_obj)
        if not recovery_email:
            return render(request, 'guest/forgot_password.html', {
                'error': 'No recovery email is available for this account. Please contact administrator.'
            })

        signer = TimestampSigner()
        token = signer.sign(str(login_obj.LoginID))
        reset_link = request.build_absolute_uri(
            f"{reverse('reset_password')}?token={token}"
        )

        subject = 'ResQlink | Password Reset Request'
        body = (
            'A password reset was requested for your ResQlink account.\n\n'
            f'Username: {login_obj.Username}\n\n'
            f'Use this link to reset your password (valid for 30 minutes):\n{reset_link}\n\n'
            'If you did not request this, please ignore this email.'
        )

        try:
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [recovery_email],
                fail_silently=False,
            )
        except Exception:
            return render(request, 'guest/forgot_password.html', {
                'error': 'Unable to send reset email right now. Please try again later.'
            })

        return render(request, 'guest/forgot_password.html', {
            'success': 'If the account exists, a password reset link has been sent to the registered email.'
        })

    return render(request, 'guest/forgot_password.html')


def reset_password(request):
    token = request.GET.get('token') if request.method == 'GET' else request.POST.get('token')

    if not token:
        return render(request, 'guest/reset_password.html', {
            'error': 'Invalid password reset link.'
        })

    signer = TimestampSigner()

    try:
        login_id = signer.unsign(token, max_age=1800)
        login_obj = tbl_login.objects.filter(LoginID=login_id).first()
        if not login_obj:
            raise BadSignature
    except SignatureExpired:
        return render(request, 'guest/reset_password.html', {
            'error': 'This password reset link has expired. Please request a new one.'
        })
    except BadSignature:
        return render(request, 'guest/reset_password.html', {
            'error': 'Invalid password reset link.'
        })

    if request.method == 'POST':
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not new_password or not confirm_password:
            return render(request, 'guest/reset_password.html', {
                'error': 'Please fill in both password fields.',
                'token': token,
            })

        if len(new_password) < 6:
            return render(request, 'guest/reset_password.html', {
                'error': 'Password must be at least 6 characters long.',
                'token': token,
            })

        if new_password != confirm_password:
            return render(request, 'guest/reset_password.html', {
                'error': 'Passwords do not match.',
                'token': token,
            })

        login_obj.Password = new_password
        login_obj.save(update_fields=['Password'])

        return render(request, 'guest/login.html', {
            'success': 'Password reset successful. Please login with your new password.'
        })

    return render(request, 'guest/reset_password.html', {'token': token})

def volunteer_reg(request):
    taluks = tbl_taluk.objects.all()
    localbodies = tbl_localbody.objects.all()
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            date_of_birth = request.POST.get('date_of_birth')
            age = request.POST.get('age')
            contact_number1 = request.POST.get('phone')
            email = request.POST.get('email')
            taluk_id = request.POST.get('taluk')
            localbody_id = request.POST.get('localbody')
            address = request.POST.get('address')
            skills = request.POST.get('skills')
            username = request.POST.get('username')
            password = request.POST.get('password')
            photo = request.FILES.get('photo')
            id_proof = request.FILES.get('id_proof')
            availability_status='Available'


            # Validate required fields
            if not all([name, date_of_birth, age, contact_number1, email, taluk_id, localbody_id, address, skills, username, password, photo, id_proof]):   
                return render(request, 'guest/volunteer_reg.html', {
                    'taluks': taluks,
                    'localbodies': localbodies,
                    'error': 'All fields including photo and identity proof are required.'

                })
            
            # Get Taluk and Local Body objects
            taluk = tbl_taluk.objects.get(TalukID=taluk_id)
            localbody = tbl_localbody.objects.get(LocalbodyID=localbody_id)

            # Check if username already exists
            if tbl_login.objects.filter(Username=username).exists():
                return render (request, 'guest/volunteer_reg.html', {
                    'taluks': taluks,
                    'localbodies': localbodies,
                    'error': 'Username already exists. Please choose a different username.'
                })
            
            # Create login entry
            login = tbl_login.objects.create(
                Username=username,
                Password=password,
                Role='VOLUNTEER',
                Status='Pending'
            )

            # Create Volunteer registration entry
            volunteer_registaration = tbl_volunteer_reg.objects.create(
                LoginId=login,
                Name=name,
                DateofBirth=date_of_birth,
                age=age,
                ContactNumber1=contact_number1,
                Email=email,
                TalukID=taluk,
                LocalbodyID=localbody,
                Address=address,
                skills=skills,
                vol_image=photo,
                identity_proof=id_proof,
                availability_status=availability_status
            )
            return render(request, 'guest/volunteer_reg.html', {
                'taluks': taluks,
                'localbodies': localbodies,
                'success': 'Registration successful! Your volunteer account has been created. Please login with your credentials.'
            })
        
        except tbl_taluk.DoesNotExist:
            return render(request, 'guest/volunteer_reg.html', {
                'taluks': taluks,
                'localbodies': localbodies,
                'error': 'Selected Taluk does not exist.'
            })
        except tbl_localbody.DoesNotExist:
            return render(request, 'guest/volunteer_reg.html', {
                'taluks': taluks,
                'localbodies': localbodies,
                'error': 'Selected Local Body does not exist.'
            })
        except Exception as e:
            return render(request, 'guest/volunteer_reg.html', {
                'taluks': taluks,
                'localbodies': localbodies,
                'error': f'Registration failed: {str(e)}'
            })
    return render(request, 'guest/volunteer_reg.html', {'taluks': taluks, 'localbodies': localbodies})


def helpreq(request):
    taluks = tbl_taluk.objects.all()
    localbodies = tbl_localbody.objects.all()
    disasters = tbl_disaster.objects.all()
    service_types = tbl_service_type.objects.all()
    return render(request, 'guest/helprequest.html', {
        'taluks': taluks,
        'localbodies': localbodies,
        'disasters': disasters,
        'service_types': service_types,
    })


def get_localbodies_by_taluk(request, taluk_id):
    """API endpoint to get localbodies filtered by taluk"""
    try:
        localbodies = tbl_localbody.objects.filter(TalukId=taluk_id).values('LocalbodyID', 'LocalbodyName')
        return JsonResponse(list(localbodies), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def get_wards_by_localbody(request, localbody_id):
    """API endpoint to get wards filtered by localbody"""
    try:
        wards = tbl_ward.objects.filter(LocalbodyID=localbody_id).values('WardID', 'WardNumber')
        return JsonResponse(list(wards), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

