from django.db import models

# Create your models here.
# Login Table
class tbl_login(models.Model):
    LoginID = models.AutoField(primary_key=True)
    Username = models.CharField(max_length=100)
    Password = models.CharField(max_length=100)
    Role = models.CharField(max_length=100)
    Status = models.CharField(max_length=50)

# NGO Registration Table
class tbl_ngo_reg(models.Model):
    NGOID = models.AutoField(primary_key=True)
    LoginID = models.ForeignKey(tbl_login, on_delete=models.CASCADE)
    NGOname = models.CharField(max_length=200)
    RegNumber = models.CharField(max_length=100)
    TalukID = models.ForeignKey('adminapp.tbl_taluk', on_delete=models.CASCADE)
    LocalbodyID = models.ForeignKey('adminapp.tbl_localbody', on_delete=models.CASCADE)
    Address = models.CharField(max_length=300)
    ContactNumber1 = models.CharField(max_length=15)
    ContactNumber2 = models.CharField(max_length=15, blank=True, null=True)
    Email = models.CharField(max_length=100)    
    ProofDocument = models.FileField(upload_to='ngo_proofs/')
    hasVolunteers = models.CharField(max_length=10)  # 'Yes' or 'No'

# Volunteer Registration Table
class tbl_volunteer_reg(models.Model):
    VolunteerId = models.AutoField(primary_key=True)
    LoginId = models.ForeignKey(tbl_login, on_delete=models.CASCADE)
    Name = models.CharField(max_length=200)
    DateofBirth = models.DateField()
    age = models.IntegerField()
    ContactNumber1 = models.CharField(max_length=15)
    Email = models.CharField(max_length=100)
    TalukID = models.ForeignKey('adminapp.tbl_taluk', on_delete=models.CASCADE)
    LocalbodyID = models.ForeignKey('adminapp.tbl_localbody', on_delete=models.CASCADE)
    Address = models.CharField(max_length=300)
    skills = models.CharField(max_length=300)
    identity_proof = models.FileField(upload_to='volunteer_id_proofs/', null=True, blank=True)
    vol_image = models.FileField(upload_to='volunteer_images/', null=True, blank=True)
    availability_status = models.CharField(max_length=20, default='Available')

class tbl_affected_individual(models.Model):
    affectedID = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    age = models.IntegerField(null=False, blank=False)
    gender = models.CharField(max_length=10)
    contact_number = models.CharField(max_length=15)
    address = models.CharField(max_length=300)
    talukID = models.ForeignKey('adminapp.tbl_taluk', on_delete=models.CASCADE)
    localbodyID = models.ForeignKey('adminapp.tbl_localbody', on_delete=models.CASCADE)
    wardID = models.ForeignKey('adminapp.tbl_ward', on_delete=models.CASCADE)

class tbl_community_request(models.Model):
    campID = models.AutoField(primary_key=True)
    community_name = models.CharField(max_length=200, null=True, blank=True)
    coordinator_name = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=15)
    address = models.CharField(max_length=300)
    talukID = models.ForeignKey('adminapp.tbl_taluk', on_delete=models.CASCADE)
    localbodyID =  models.ForeignKey('adminapp.tbl_localbody', on_delete=models.CASCADE)
    wardID = models.ForeignKey('adminapp.tbl_ward', on_delete=models.CASCADE)
    estimated_people = models.IntegerField()
    is_verified = models.CharField(max_length=10)  # 'Yes' or 'No'

class tbl_request(models.Model):
    request_id = models.AutoField(primary_key=True)
    request_type = models.CharField(max_length=100)
    affectedID = models.ForeignKey(tbl_affected_individual, on_delete=models.CASCADE, null=True, blank=True)
    campID = models.ForeignKey(tbl_community_request, on_delete=models.CASCADE, null=True, blank=True)
    disasterID = models.ForeignKey('adminapp.tbl_disaster', on_delete=models.CASCADE, null=True, blank=True)
    request_status = models.CharField(max_length=50) 
    NGOID = models.ForeignKey('guestapp.tbl_ngo_reg', on_delete=models.CASCADE, null=True, blank=True)  # e.g., 'Pending', 'Approved', 'Rejected'

class tbl_request_service(models.Model):
    request_service_id = models.AutoField(primary_key=True)
    requestID = models.ForeignKey(tbl_request, on_delete=models.CASCADE, null=True, blank=True)
    serviceID = models.ForeignKey('adminapp.tbl_service_type', on_delete=models.CASCADE, null=True, blank=True)
    categoryID = models.ForeignKey('adminapp.tbl_category', on_delete=models.CASCADE, null=True, blank=True)
    subCategoryID = models.ForeignKey('adminapp.tbl_subcategory', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    fulfilled_quantity = models.IntegerField(default=0)
    status = models.CharField(max_length=50) 
    
class tbl_request_assignment(models.Model): 
    assignmentID = models.AutoField(primary_key=True)
    NGOID = models.ForeignKey(tbl_ngo_reg, on_delete=models.CASCADE, null=True, blank=True)
    assigned_quntity = models.IntegerField(null=True, blank=True)
    assignment_status = models.CharField(max_length=50)
    request_serviceID = models.ForeignKey(tbl_request_service, on_delete=models.CASCADE, null=True, blank=True)
    volunteerID = models.ForeignKey(tbl_volunteer_reg, on_delete=models.CASCADE, null=True, blank=True)

class tbl_ngo_request_notification(models.Model):
    notification_id = models.AutoField(primary_key=True)
    requestID = models.ForeignKey('tbl_request', on_delete=models.CASCADE)
    NGOID = models.ForeignKey('guestapp.tbl_ngo_reg', on_delete=models.CASCADE)
    notified_at = models.DateTimeField(auto_now_add=True)
    response_status = models.CharField( max_length=20,default='Pending')  
    response_at = models.DateTimeField(null=True, blank=True)

class tbl_ngo_volunteer_assignment(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    NGOID = models.ForeignKey(tbl_ngo_reg, on_delete=models.CASCADE)
    VolunteerID = models.ForeignKey(tbl_volunteer_reg, on_delete=models.CASCADE, unique=True)  # One volunteer = One NGO only
    assignment_type = models.CharField(max_length=20, choices=[('Permanent', 'Permanent'), ('Emergency', 'Emergency')], default='Permanent')
    assignment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Inactive', 'Inactive')], default='Active')
    
    class Meta:
        unique_together = ('NGOID', 'VolunteerID')  # Ensure only one assignment per NGO-Volunteer pair






    