from django.contrib import admin

from .models import Location, AudioGuide, SubscriptionPlan, UserProfile, FavoriteLocation


class AudioGuideInline(admin.StackedInline):
    model = AudioGuide
    extra = 0


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'created_at')
    search_fields = ('title', 'city')
    inlines = [AudioGuideInline]


@admin.register(AudioGuide)
class AudioGuideAdmin(admin.ModelAdmin):
    list_display = ('location', 'language', 'voice_name', 'created_at')
    list_filter = ('language',)
    search_fields = ('location__title',)


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
