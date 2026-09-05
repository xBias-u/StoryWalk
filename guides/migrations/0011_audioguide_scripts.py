from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('guides', '0010_location_editorial_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='audioguide',
            name='long_script',
            field=models.TextField(blank=True, verbose_name='Длинный сценарий'),
        ),
        migrations.AddField(
            model_name='audioguide',
            name='short_script',
            field=models.TextField(blank=True, verbose_name='Короткий сценарий'),
        ),
    ]
