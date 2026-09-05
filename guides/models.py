from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db import transaction
from django.urls import reverse


class Location(models.Model):
    CONTENT_STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('researched', 'Факты проверены'),
        ('scripted', 'Сценарий готов'),
        ('voiced', 'Озвучено'),
        ('published', 'Опубликовано'),
    ]

    SEGMENT_CHOICES = [
        ('solo', 'Самостоятельные путешественники'),
        ('family', 'Семьи и пары'),
        ('mixed', 'Смешанный сегмент'),
    ]

    ACCESS_CHOICES = [
        ('free', 'Базовый (бесплатно)'),
        ('paid', 'Расширенный (по подписке)'),
    ]

    title = models.CharField('Название локации', max_length=200)
    city = models.CharField('Город', max_length=120, blank=True)
    short_description = models.CharField('Короткое описание', max_length=255)
    full_description = models.TextField('Полное описание')
    image = models.ImageField('Изображение', upload_to='locations/', blank=True, null=True)
    latitude = models.DecimalField(
        'Широта',
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        'Долгота',
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    story_angle = models.CharField(
        'Главная идея истории',
        max_length=255,
        blank=True,
        help_text='Одна мысль, которую слушатель унесёт с собой после этой остановки.',
    )
    content_status = models.CharField(
        'Редакционный статус',
        max_length=16,
        choices=CONTENT_STATUS_CHOICES,
        default='draft',
    )
    editorial_notes = models.TextField(
        'Заметки редактора',
        blank=True,
        help_text='Внутренние замечания, сомнительные факты и задачи перед публикацией.',
    )
    is_published = models.BooleanField(
        'Показывать пользователям',
        default=False,
        help_text='Включайте только после редакционной проверки карточки, сценария и аудио.',
    )
    is_featured = models.BooleanField('Фича/рекомендация', default=False)
    segment = models.CharField(
        'Целевой сегмент',
        max_length=16,
        choices=SEGMENT_CHOICES,
        default='solo',
        help_text='Сегмент из Lean Canvas: кто чаще всего слушает этот гид.',
    )
    access_level = models.CharField(
        'Уровень доступа',
        max_length=8,
        choices=ACCESS_CHOICES,
        default='free',
        help_text='Логика фримиум: базовые гиды бесплатно, расширенные — по подписке.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', 'title']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_published=False) | models.Q(content_status='published'),
                name='published_location_has_published_status',
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None

    def content_readiness_issues(self):
        issues = []
        if not self.has_coordinates:
            issues.append('нет координат')
        if not self.story_angle.strip():
            issues.append('нет главной идеи')
        if self.pk and self.sources.count() < 2:
            issues.append('меньше двух источников')
        guide = getattr(self, 'audio_guide', None) if self.pk else None
        if not guide or not (guide.short_script.strip() or guide.long_script.strip()):
            issues.append('нет сценария')
        if not guide or not (guide.audio_short_file or guide.audio_long_file):
            issues.append('нет аудио')
        return issues

    def publication_issues(self):
        issues = self.content_readiness_issues()
        if self.content_status != 'published':
            issues.insert(0, 'статус не «Опубликовано»')
        return issues

    def clean(self):
        super().clean()
        if self.is_published and self.content_status != 'published':
            raise ValidationError({
                'is_published': 'Публикация возможна только с редакционным статусом «Опубликовано».',
            })


class AudioGuide(models.Model):
    CHANNEL_CHOICES = [
        ('site', 'Сайт StoryWalk'),
        ('email', 'Email-рассылка'),
        ('social', 'Соцсети'),
        ('thematic', 'Тематические каналы'),
    ]

    location = models.OneToOneField(Location, on_delete=models.CASCADE, related_name='audio_guide')
    language = models.CharField('Язык', max_length=16, default='ru')
    voice_name = models.CharField('Голос ИИ', max_length=80, blank=True)
    short_script = models.TextField('Короткий сценарий', blank=True)
    long_script = models.TextField('Длинный сценарий', blank=True)
    audio_file = models.FileField('Аудиофайл (mp3)', upload_to='audio_guides/', blank=True)
    audio_short_file = models.FileField('Короткая версия (mp3)', upload_to='audio_guides/', blank=True, null=True)
    audio_long_file = models.FileField('Длинная версия (mp3)', upload_to='audio_guides/', blank=True, null=True)
    duration_seconds = models.PositiveIntegerField('Длительность (сек.)', default=0)
    source_url = models.URLField('Источник текста', blank=True)
    acquisition_channel = models.CharField(
        'Основной канал привлечения',
        max_length=16,
        choices=CHANNEL_CHOICES,
        default='site',
        help_text='Канал из Lean Canvas, через который пользователь пришёл к этому гиду.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location.title} ({self.language})"

    @property
    def has_audio(self):
        return bool(self.audio_short_file or self.audio_long_file or self.audio_file)


class AudioListenEvent(models.Model):
    EVENT_CHOICES = [
        ('start', 'Старт прослушивания'),
        ('progress', 'Прогресс прослушивания'),
        ('complete', 'Завершение прослушивания'),
    ]

    VARIANT_CHOICES = [
        ('short', 'Короткая история'),
        ('long', 'Полная история'),
        ('route', 'История в маршруте'),
        ('legacy', 'Аудио без версии'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='listen_events')
    event_type = models.CharField(max_length=12, choices=EVENT_CHOICES)
    session_id = models.CharField(max_length=64, blank=True, db_index=True)
    audio_variant = models.CharField(max_length=12, choices=VARIANT_CHOICES, default='legacy')
    current_seconds = models.FloatField(default=0, validators=[MinValueValidator(0)])
    duration_seconds = models.FloatField(default=0, validators=[MinValueValidator(0)])
    completion_percent = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['location', 'event_type', '-created_at'], name='audio_event_lookup_idx'),
        ]

    def clean(self):
        super().clean()
        if self.duration_seconds and self.current_seconds > self.duration_seconds + 1:
            raise ValidationError({
                'current_seconds': 'Текущая позиция не может быть больше длительности аудио.',
            })


class LocationImage(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField('Изображение', upload_to='locations/gallery/')
    caption = models.CharField('Подпись', max_length=140, blank=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.location.title} #{self.id}"


class LocationSource(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='sources')
    title = models.CharField('Название источника', max_length=240)
    url = models.URLField('Ссылка')
    publisher = models.CharField('Издатель', max_length=160, blank=True)
    is_primary = models.BooleanField(
        'Основной источник',
        default=False,
        help_text='Официальный сайт объекта, архив, музей или первичный документ.',
    )
    checked_at = models.DateField('Проверено', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'publisher', 'title']
        constraints = [
            models.UniqueConstraint(fields=['location', 'url'], name='unique_source_per_location'),
        ]

    def __str__(self):
        return f"{self.location.title}: {self.title}"


class PlaceCandidate(models.Model):
    STATUS_CHOICES = [
        ('new', 'Найдено'),
        ('shortlisted', 'В шорт-листе'),
        ('rejected', 'Отклонено'),
        ('imported', 'Создан черновик'),
    ]

    CATEGORY_CHOICES = [
        ('historic', 'Историческое место'),
        ('museum', 'Музей'),
        ('architecture', 'Архитектура'),
        ('memorial', 'Памятник'),
        ('artwork', 'Городское искусство'),
        ('religious', 'Религиозная архитектура'),
        ('other', 'Другое'),
    ]

    name = models.CharField('Название', max_length=200)
    city = models.CharField('Город', max_length=120, blank=True)
    latitude = models.DecimalField('Широта', max_digits=9, decimal_places=6)
    longitude = models.DecimalField('Долгота', max_digits=9, decimal_places=6)
    category = models.CharField('Категория', max_length=16, choices=CATEGORY_CHOICES, default='other')
    distance_m = models.PositiveIntegerField('Расстояние по прямой, м', default=0)
    story_score = models.PositiveSmallIntegerField('Потенциал истории', default=0)
    source_provider = models.CharField('Источник данных', max_length=32, default='openstreetmap')
    source_id = models.CharField('ID во внешнем источнике', max_length=80)
    source_url = models.URLField('Карточка источника')
    source_tags = models.JSONField('Исходные теги', default=dict, blank=True)
    status = models.CharField('Статус', max_length=16, choices=STATUS_CHOICES, default='new')
    location = models.OneToOneField(
        Location,
        on_delete=models.SET_NULL,
        related_name='discovery_candidate',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-story_score', 'distance_m', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['source_provider', 'source_id'],
                name='unique_place_candidate_source',
            ),
        ]

    def __str__(self):
        return self.name

    @transaction.atomic
    def promote_to_location(self):
        if self.location_id:
            return self.location
        if Location.objects.filter(title__iexact=self.name, city__iexact=self.city).exists():
            raise ValueError('Локация с таким названием уже существует в этом городе')

        location = Location.objects.create(
            title=self.name,
            city=self.city,
            short_description=f'Черновик истории места «{self.name}».',
            full_description='',
            latitude=self.latitude,
            longitude=self.longitude,
            content_status='draft',
            is_published=False,
            editorial_notes='Проверьте название, найдите минимум два источника и сформулируйте главную идею истории.',
        )
        LocationSource.objects.create(
            location=location,
            title=f'{self.name} в OpenStreetMap',
            publisher='OpenStreetMap contributors',
            url=self.source_url,
            is_primary=False,
        )
        self.location = location
        self.status = 'imported'
        self.save(update_fields=['location', 'status', 'updated_at'])
        return location


class WalkRoute(models.Model):
    ROUTING_STATUS_CHOICES = [
        ('draft', 'Маршрут не рассчитан'),
        ('estimated', 'Переходы оценены'),
        ('verified', 'Проверено по пешеходным дорогам'),
    ]

    INTEREST_CHOICES = [
        ('architecture', 'Архитектура'),
        ('history', 'История'),
        ('art', 'Искусство'),
        ('local', 'Городские истории'),
    ]

    title = models.CharField('Название прогулки', max_length=180)
    slug = models.SlugField('Адрес страницы', max_length=180, unique=True)
    city = models.CharField('Город', max_length=120)
    district = models.CharField('Район', max_length=120, blank=True)
    summary = models.TextField('Короткое описание')
    duration_minutes = models.PositiveSmallIntegerField('Продолжительность, мин', default=60)
    distance_km = models.DecimalField('Расстояние, км', max_digits=4, decimal_places=1, default=0)
    interest = models.CharField('Главная тема', max_length=24, choices=INTEREST_CHOICES, default='history')
    routing_status = models.CharField(
        'Статус навигации',
        max_length=16,
        choices=ROUTING_STATUS_CHOICES,
        default='draft',
    )
    route_geometry = models.JSONField(
        'Геометрия маршрута',
        default=dict,
        blank=True,
        help_text='GeoJSON пешеходной линии, полученный от маршрутизатора.',
    )
    routing_provider = models.CharField('Маршрутизатор', max_length=40, blank=True)
    routing_updated_at = models.DateTimeField('Маршрут рассчитан', blank=True, null=True)
    is_published = models.BooleanField('Опубликован', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_published', 'title']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_published=False) | models.Q(routing_status='verified'),
                name='published_route_is_verified',
            ),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('route_preview', kwargs={'slug': self.slug})

    def publication_issues(self):
        issues = []
        if self.routing_status != 'verified':
            issues.append('пешеходный путь не проверен')
        if self.pk:
            stops = list(self.stops.select_related('location'))
            if len(stops) < 2:
                issues.append('меньше двух остановок')
            unavailable = [stop.location.title for stop in stops if not stop.location.is_published]
            if unavailable:
                issues.append('не опубликованы точки: ' + ', '.join(unavailable))
        return issues

    def clean(self):
        super().clean()
        if self.is_published and self.routing_status != 'verified':
            raise ValidationError({
                'is_published': 'Публиковать можно только проверенный пешеходный маршрут.',
            })


class RouteStop(models.Model):
    route = models.ForeignKey(WalkRoute, on_delete=models.CASCADE, related_name='stops')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='route_stops')
    position = models.PositiveSmallIntegerField('Номер остановки', validators=[MinValueValidator(1)])
    walk_minutes = models.PositiveSmallIntegerField('Минут пешком от предыдущей точки', default=0)
    walk_distance_m = models.PositiveIntegerField('Расстояние от предыдущей точки, м', default=0)
    navigation_hint = models.CharField('Как дойти', max_length=255, blank=True)
    observation_prompt = models.CharField('На что посмотреть', max_length=255, blank=True)

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['route', 'position'], name='unique_route_stop_position'),
            models.UniqueConstraint(fields=['route', 'location'], name='unique_location_per_route'),
        ]

    def __str__(self):
        return f"{self.route.title}: {self.position}. {self.location.title}"


class SubscriptionPlan(models.Model):
    name = models.CharField('Название тарифа', max_length=120)
    price_rub = models.PositiveIntegerField('Цена в месяц (₽)', default=0)
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Доступен', default=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True, null=True)
    bio = models.CharField('Коротко о себе', max_length=240, blank=True)

    def __str__(self):
        return f"Profile: {self.user.username}"


class FavoriteLocation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_locations')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='liked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'location')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} ♥ {self.location.title}"
