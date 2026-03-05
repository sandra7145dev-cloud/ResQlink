from django.db import models

# Create your models here.
#Table For Panchayat

class tbl_taluk(models.Model):
    TalukID=models.AutoField(primary_key=True)
    TalukName=models.CharField(max_length=100)

class tbl_localbody_type(models.Model):
    TypeID=models.AutoField(primary_key=True)
    TypeName=models.CharField(max_length=100)

class tbl_localbody(models.Model):
    LocalbodyID=models.AutoField(primary_key=True)
    LocalbodyName=models.CharField(max_length=100)
    TypeID=models.ForeignKey(tbl_localbody_type, on_delete=models.CASCADE)
    TalukId=models.ForeignKey(tbl_taluk, on_delete=models.CASCADE)

class tbl_ward(models.Model):
    WardID = models.AutoField(primary_key=True)
    WardNumber = models.CharField(max_length=10)
    LocalbodyID = models.ForeignKey(tbl_localbody, on_delete=models.CASCADE)


class tbl_category(models.Model):
    CategoryID = models.AutoField(primary_key=True)
    CategoryName = models.CharField(max_length=100)

class tbl_subcategory(models.Model):
    subCategoryId = models.AutoField(primary_key=True)
    SubCategoryname = models.CharField(max_length=100)
    categoryID = models.ForeignKey(tbl_category, on_delete=models.CASCADE)
    min_required_quantity = models.IntegerField(null=False)
    is_broadcasted = models.BooleanField(default=False)

class tbl_disaster(models.Model):
    DisasterID = models.AutoField(primary_key=True)
    DisasterName = models.CharField(max_length=100)

class tbl_service_type(models.Model):
    serviceID = models.AutoField(primary_key=True)
    serviceName = models.CharField(max_length=100)
