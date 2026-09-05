from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('guides', '0007_locationimage'),
    ]

    operations = [
        migrations.RenameField(
            model_name='subscriptionplan',
            old_name='is_demo',
            new_name='is_active',
        ),
        migrations.AlterField(
            model_name='subscriptionplan',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Доступен'),
        ),
    ]
