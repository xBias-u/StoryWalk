from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('guides', '0013_route_navigation_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='audioguide',
            name='audio_file',
            field=models.FileField(blank=True, upload_to='audio_guides/', verbose_name='Аудиофайл (mp3)'),
        ),
        migrations.AddField(
            model_name='walkroute',
            name='route_geometry',
            field=models.JSONField(blank=True, default=dict, help_text='GeoJSON пешеходной линии, полученный от маршрутизатора.', verbose_name='Геометрия маршрута'),
        ),
        migrations.AddField(
            model_name='walkroute',
            name='routing_provider',
            field=models.CharField(blank=True, max_length=40, verbose_name='Маршрутизатор'),
        ),
        migrations.AddField(
            model_name='walkroute',
            name='routing_updated_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Маршрут рассчитан'),
        ),
    ]
