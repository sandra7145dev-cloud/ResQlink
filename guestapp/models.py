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
    availability_status = models.CharField(max_length=100)


    