from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('guides', '0012_placecandidate_location_is_published'),
    ]

    operations = [
        migrations.AddField(
            model_name='routestop',
            name='walk_distance_m',
            field=models.PositiveIntegerField(default=0, verbose_name='Расстояние от предыдущей точки, м'),
        ),
        migrations.AddField(
            model_name='walkroute',
            name='routing_status',
            field=models.CharField(choices=[('draft', 'Маршрут не рассчитан'), ('estimated', 'Переходы оценены'), ('verified', 'Проверено по пешеходным дорогам')], default='draft', max_length=16, verbose_name='Статус навигации'),
        ),
    ]
