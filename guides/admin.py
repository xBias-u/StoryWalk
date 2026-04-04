from django.contrib import admin

from .models import Location, AudioGuide, SubscriptionPlan, UserProfile, FavoriteLocation, AudioListenEvent, LocationImage


class AudioGuideInline(admin.StackedInline):
    model = AudioGuide
    extra = 0


class LocationImageInline(admin.TabularInline):
    model = LocationImage
    extra = 0


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'is_featured', 'segment', 'access_level', 'created_at')
    search_fields = ('title', 'city')
    list_filter = ('is_featured', 'city', 'segment', 'access_level')
    inlines = [AudioGuideInline, LocationImageInline]
    fieldsets = (
        ('Основное', {'fields': ('title', 'city', 'short_description', 'full_description', 'image')}),
        ('Lean Canvas метки', {'fields': ('is_featured', 'segment', 'access_level')}),
    )


@admin.register(AudioGuide)
class AudioGuideAdmin(admin.ModelAdmin):
    list_display = ('location', 'language', 'voice_name', 'acquisition_channel', 'created_at')
    list_filter = ('language', 'acquisition_channel')
    search_fields = ('location__title',)


@admin.register(AudioListenEvent)
class AudioListenEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event_type', 'location', 'user', 'completion_percent')
    list_filter = ('event_type', 'location')
    search_fields = ('location__title', 'user__username')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_rub', 'is_demo')
    list_filter = ('is_demo',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')
    search_fields = ('user__username', 'bio')


@admin.register(FavoriteLocation)
class FavoriteLocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'created_at')
    search_fields = ('user__username', 'location__title')
