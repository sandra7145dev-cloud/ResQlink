from django.shortcuts import render, redirect
from django.http import HttpResponse
from adminapp.models import tbl_taluk, tbl_localbody
from .models import tbl_login, tbl_ngo_reg, tbl_volunteer_reg
# Create your views here.

def guesthome(request):
    return render(request, 'guest/index.html')

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
    return render(request, 'guest/login.html')

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


            # Validate required fields
            if not all([name, date_of_birth, age, contact_number1, email, taluk_id, localbody_id, address, skills,  username, password]):   
                return render(request, 'guest/volunteer_reg.html', {
                    'taluks': taluks,
                    'localbodies': localbodies,
                    'error': 'All fields are required.'

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