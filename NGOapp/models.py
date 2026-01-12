from django.db import models

# Create your models here.
class tbl_ngo_helptype(models.Model):
    ngoHelpID = models.AutoField(primary_key=True)
    NGOID = models.ForeignKey('guestapp.tbl_ngo_reg', on_delete=models.CASCADE)
    categoryID = models.ForeignKey('adminapp.tbl_category', on_delete=models.CASCADE, null=True, blank=True)
    subCategoryID = models.ForeignKey('adminapp.tbl_subcategory', on_delete=models.CASCADE, null=True, blank=True)
    serviceID = models.ForeignKey('adminapp.tbl_service_type', on_delete=models.CASCADE, null=True, blank=True)
    isActive = models.CharField(max_length=10, default='Yes')
    quantity = models.CharField(max_length=25, null=True, blank=True, default='')  # 'Yes' or 'No'
