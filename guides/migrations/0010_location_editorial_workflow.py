import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('guides', '0009_walkroute_routestop'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='content_status',
            field=models.CharField(
                choices=[
                    ('draft', 'Черновик'),
                    ('researched', 'Факты проверены'),
                    ('scripted', 'Сценарий готов'),
                    ('voiced', 'Озвучено'),
                    ('published', 'Опубликовано'),
                ],
                default='draft',
                max_length=16,
                verbose_name='Редакционный статус',
            ),
        ),
        migrations.AddField(
            model_name='location',
            name='editorial_notes',
            field=models.TextField(
                blank=True,
                help_text='Внутренние замечания, сомнительные факты и задачи перед публикацией.',
                verbose_name='Заметки редактора',
            ),
        ),
        migrations.AddField(
            model_name='location',
            name='latitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name='Широта',
            ),
        ),
        migrations.AddField(
            model_name='location',
            name='longitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name='Долгота',
            ),
        ),
        migrations.AddField(
            model_name='location',
            name='story_angle',
            field=models.CharField(
                blank=True,
                help_text='Одна мысль, которую слушатель унесёт с собой после этой остановки.',
                max_length=255,
                verbose_name='Главная идея истории',
            ),
        ),
        migrations.CreateModel(
            name='LocationSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=240, verbose_name='Название источника')),
                ('url', models.URLField(verbose_name='Ссылка')),
                ('publisher', models.CharField(blank=True, max_length=160, verbose_name='Издатель')),
                ('is_primary', models.BooleanField(default=False, help_text='Официальный сайт объекта, архив, музей или первичный документ.', verbose_name='Основной источник')),
                ('checked_at', models.DateField(blank=True, null=True, verbose_name='Проверено')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sources', to='guides.location')),
            ],
            options={'ordering': ['-is_primary', 'publisher', 'title']},
        ),
        migrations.AddConstraint(
            model_name='locationsource',
            constraint=models.UniqueConstraint(fields=('location', 'url'), name='unique_source_per_location'),
        ),
    ]
