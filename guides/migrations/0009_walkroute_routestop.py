import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('guides', '0008_rename_subscriptionplan_is_demo_is_active'),
    ]

    operations = [
        migrations.CreateModel(
            name='WalkRoute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=180, verbose_name='Название прогулки')),
                ('slug', models.SlugField(max_length=180, unique=True, verbose_name='Адрес страницы')),
                ('city', models.CharField(max_length=120, verbose_name='Город')),
                ('district', models.CharField(blank=True, max_length=120, verbose_name='Район')),
                ('summary', models.TextField(verbose_name='Короткое описание')),
                ('duration_minutes', models.PositiveSmallIntegerField(default=60, verbose_name='Продолжительность, мин')),
                ('distance_km', models.DecimalField(decimal_places=1, default=0, max_digits=4, verbose_name='Расстояние, км')),
                ('interest', models.CharField(choices=[('architecture', 'Архитектура'), ('history', 'История'), ('art', 'Искусство'), ('local', 'Городские истории')], default='history', max_length=24, verbose_name='Главная тема')),
                ('is_published', models.BooleanField(default=False, verbose_name='Опубликован')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-is_published', 'title']},
        ),
        migrations.CreateModel(
            name='RouteStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveSmallIntegerField(verbose_name='Номер остановки')),
                ('walk_minutes', models.PositiveSmallIntegerField(default=0, verbose_name='Минут пешком от предыдущей точки')),
                ('navigation_hint', models.CharField(blank=True, max_length=255, verbose_name='Как дойти')),
                ('observation_prompt', models.CharField(blank=True, max_length=255, verbose_name='На что посмотреть')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='route_stops', to='guides.location')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stops', to='guides.walkroute')),
            ],
            options={'ordering': ['position']},
        ),
        migrations.AddConstraint(
            model_name='routestop',
            constraint=models.UniqueConstraint(fields=('route', 'position'), name='unique_route_stop_position'),
        ),
        migrations.AddConstraint(
            model_name='routestop',
            constraint=models.UniqueConstraint(fields=('route', 'location'), name='unique_location_per_route'),
        ),
    ]
