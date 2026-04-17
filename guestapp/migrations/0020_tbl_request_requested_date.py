from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('guestapp', '0019_tbl_ngo_volunteer_assignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='tbl_request',
            name='requested_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
