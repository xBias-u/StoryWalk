from django.conf import settings
from django.db import models


class Location(models.Model):
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

    def __str__(self):
        return self.title


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
    audio_file = models.FileField('Аудиофайл (mp3)', upload_to='audio_guides/')
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


class AudioListenEvent(models.Model):
    EVENT_CHOICES = [
        ('start', 'Старт прослушивания'),
        ('progress', 'Прогресс прослушивания'),
        ('complete', 'Завершение прослушивания'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='listen_events')
    event_type = models.CharField(max_length=12, choices=EVENT_CHOICES)
    current_seconds = models.FloatField(default=0)
    duration_seconds = models.FloatField(default=0)
    completion_percent = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SubscriptionPlan(models.Model):
    name = models.CharField('Название тарифа', max_length=120)
    price_rub = models.PositiveIntegerField('Цена в месяц (₽)', default=0)
    description = models.TextField('Описание', blank=True)
    is_demo = models.BooleanField('Демо-тариф', default=True)

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
