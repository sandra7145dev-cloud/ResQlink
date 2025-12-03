from django.db import models

# Create your models here.
#Table For Panchayat
class tbl_panchayat(models.Model):
    PanchayatID=models.AutoField(primary_key=True)
    PanchayatName=models.CharField(max_length=100)

class tbl_location(models.Model):
    LocationID=models.AutoField(primary_key=True)
    LocationName=models.CharField(max_length=100)