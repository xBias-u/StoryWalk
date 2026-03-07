from django.contrib import admin
from .models import Location, AudioGuide, SubscriptionPlan


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'created_at')
    search_fields = ('title', 'city')


@admin.register(AudioGuide)
class AudioGuideAdmin(admin.ModelAdmin):
    list_display = ('location', 'language', 'voice_name', 'created_at')
    list_filter = ('language',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_rub', 'is_demo')
    list_filter = ('is_demo',)
