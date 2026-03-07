from django.db import models


class Location(models.Model):
    title = models.CharField(max_length=200)
    city = models.CharField(max_length=120, blank=True)
    short_description = models.CharField(max_length=255)
    full_description = models.TextField()
    image = models.ImageField(upload_to='locations/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class AudioGuide(models.Model):
    location = models.OneToOneField(Location, on_delete=models.CASCADE, related_name='audio_guide')
    language = models.CharField(max_length=16, default='ru')
    voice_name = models.CharField(max_length=80, blank=True)
    audio_file = models.FileField(upload_to='audio_guides/')
    duration_seconds = models.PositiveIntegerField(default=0)
    source_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location.title} ({self.language})"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=120)
    price_rub = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    is_demo = models.BooleanField(default=True)

    def __str__(self):
        return self.name
