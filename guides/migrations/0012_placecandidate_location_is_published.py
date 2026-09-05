import django.db.models.deletion
from django.db import migrations, models


def publish_existing_locations(apps, schema_editor):
    Location = apps.get_model('guides', 'Location')
    Location.objects.update(is_published=True)


class Migration(migrations.Migration):
    dependencies = [
        ('guides', '0011_audioguide_scripts'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='is_published',
            field=models.BooleanField(default=False, help_text='Включайте только после редакционной проверки карточки, сценария и аудио.', verbose_name='Показывать пользователям'),
        ),
        migrations.RunPython(publish_existing_locations, migrations.RunPython.noop),
        migrations.CreateModel(
            name='PlaceCandidate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название')),
                ('city', models.CharField(blank=True, max_length=120, verbose_name='Город')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9, verbose_name='Широта')),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9, verbose_name='Долгота')),
                ('category', models.CharField(choices=[('historic', 'Историческое место'), ('museum', 'Музей'), ('architecture', 'Архитектура'), ('memorial', 'Памятник'), ('artwork', 'Городское искусство'), ('religious', 'Религиозная архитектура'), ('other', 'Другое')], default='other', max_length=16, verbose_name='Категория')),
                ('distance_m', models.PositiveIntegerField(default=0, verbose_name='Расстояние по прямой, м')),
                ('story_score', models.PositiveSmallIntegerField(default=0, verbose_name='Потенциал истории')),
                ('source_provider', models.CharField(default='openstreetmap', max_length=32, verbose_name='Источник данных')),
                ('source_id', models.CharField(max_length=80, verbose_name='ID во внешнем источнике')),
                ('source_url', models.URLField(verbose_name='Карточка источника')),
                ('source_tags', models.JSONField(blank=True, default=dict, verbose_name='Исходные теги')),
                ('status', models.CharField(choices=[('new', 'Найдено'), ('shortlisted', 'В шорт-листе'), ('rejected', 'Отклонено'), ('imported', 'Создан черновик')], default='new', max_length=16, verbose_name='Статус')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('location', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='discovery_candidate', to='guides.location')),
            ],
            options={'ordering': ['-story_score', 'distance_m', 'name']},
        ),
        migrations.AddConstraint(
            model_name='placecandidate',
            constraint=models.UniqueConstraint(fields=('source_provider', 'source_id'), name='unique_place_candidate_source'),
        ),
    ]
