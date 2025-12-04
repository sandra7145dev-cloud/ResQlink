from django.db import models

# Create your models here.
#Table For Panchayat
class tbl_panchayat(models.Model):
    PanchayatID=models.AutoField(primary_key=True)
    PanchayatName=models.CharField(max_length=100)

class tbl_ward(models.Model):
    WardID=models.AutoField(primary_key=True)
    WardName=models.CharField(max_length=100)
    panchayatID=models.ForeignKey(tbl_panchayat, on_delete=models.CASCADE)

class tbl_category(models.Model):
    CategoryID = models.AutoField(primary_key=True)
    CategoryName = models.CharField(max_length=100)

class tbl_subcategory(models.Model):
    subCategoryId = models.AutoField(primary_key=True)
    SubCategoryname = models.CharField(max_length=100)
    categoryID = models.ForeignKey(tbl_category, on_delete=models.CASCADE)