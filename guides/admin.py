from django import forms
from django.contrib import admin

from .models import (
    AudioGuide,
    AudioListenEvent,
    FavoriteLocation,
    Location,
    LocationImage,
    LocationSource,
    PlaceCandidate,
    RouteStop,
    SubscriptionPlan,
    UserProfile,
    WalkRoute,
)


class LocationAdminForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = '__all__'

    def _post_clean(self):
        super()._post_clean()
        if not self.cleaned_data.get('is_published'):
            return
        if not self.instance.pk:
            self.add_error('is_published', 'Сначала сохраните карточку, источники, сценарий и аудио.')
            return
        issues = self.instance.content_readiness_issues()
        if issues:
            self.add_error('is_published', 'Не готово к публикации: ' + ', '.join(issues))


class WalkRouteAdminForm(forms.ModelForm):
    class Meta:
        model = WalkRoute
        fields = '__all__'

    def _post_clean(self):
        super()._post_clean()
        if not self.cleaned_data.get('is_published'):
            return
        if not self.instance.pk:
            self.add_error('is_published', 'Сначала сохраните маршрут и его остановки.')
            return
        issues = self.instance.publication_issues()
        if issues:
            self.add_error('is_published', 'Не готово к публикации: ' + '; '.join(issues))


class AudioGuideInline(admin.StackedInline):
    model = AudioGuide
    extra = 0
    fieldsets = (
        ('Сценарии', {'fields': ('short_script', 'long_script')}),
        ('Озвучка', {'fields': (
            'language',
            'voice_name',
            'audio_short_file',
            'audio_long_file',
            'audio_file',
            'duration_seconds',
        )}),
        ('Происхождение', {'fields': ('source_url', 'acquisition_channel')}),
    )


class LocationImageInline(admin.TabularInline):
    model = LocationImage
    extra = 0


class LocationSourceInline(admin.TabularInline):
    model = LocationSource
    extra = 1
    fields = ('title', 'publisher', 'url', 'is_primary', 'checked_at')


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0
    autocomplete_fields = ('location',)
    fields = (
        'position',
        'location',
        'walk_minutes',
        'walk_distance_m',
        'navigation_hint',
        'observation_prompt',
    )


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    form = LocationAdminForm
    list_display = (
        'title',
        'city',
        'content_status',
        'coordinates_ready',
        'editorial_quality',
        'is_published',
        'is_featured',
    )
    search_fields = ('title', 'city')
    list_filter = ('is_published', 'content_status', 'is_featured', 'city', 'segment', 'access_level')
    inlines = [LocationSourceInline, AudioGuideInline, LocationImageInline]
    fieldsets = (
        ('Карточка', {'fields': ('title', 'city', 'short_description', 'full_description', 'image')}),
        ('Место на карте', {'fields': (('latitude', 'longitude'),)}),
        ('Редакция', {'fields': ('story_angle', 'content_status', 'editorial_notes', 'is_published')}),
        ('Аудитория и доступ', {'fields': ('is_featured', 'segment', 'access_level')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('audio_guide').prefetch_related('sources')

    @admin.display(boolean=True, description='Координаты')
    def coordinates_ready(self, obj):
        return obj.has_coordinates

    @admin.display(description='Готовность')
    def editorial_quality(self, obj):
        issues = obj.content_readiness_issues()
        return 'Готово' if not issues else ' · '.join(issues)


@admin.register(PlaceCandidate)
class PlaceCandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'story_score', 'distance_m', 'city', 'status')
    list_filter = ('status', 'category', 'city', 'source_provider')
    search_fields = ('name', 'city', 'source_id')
    readonly_fields = (
        'source_provider',
        'source_id',
        'source_url',
        'source_tags',
        'distance_m',
        'story_score',
        'location',
        'created_at',
        'updated_at',
    )
    actions = ('shortlist_candidates', 'reject_candidates', 'create_location_drafts')

    @admin.action(description='Добавить в шорт-лист')
    def shortlist_candidates(self, request, queryset):
        updated = queryset.exclude(status='imported').update(status='shortlisted')
        self.message_user(request, f'В шорт-лист добавлено: {updated}')

    @admin.action(description='Отклонить')
    def reject_candidates(self, request, queryset):
        updated = queryset.exclude(status='imported').update(status='rejected')
        self.message_user(request, f'Отклонено: {updated}')

    @admin.action(description='Создать неопубликованные локации')
    def create_location_drafts(self, request, queryset):
        created = 0
        skipped = []
        for candidate in queryset:
            try:
                candidate.promote_to_location()
                created += 1
            except ValueError as exc:
                skipped.append(f'{candidate.name}: {exc}')
        self.message_user(request, f'Создано черновиков: {created}')
        if skipped:
            self.message_user(request, 'Пропущено: ' + '; '.join(skipped), level='warning')


@admin.register(AudioGuide)
class AudioGuideAdmin(admin.ModelAdmin):
    list_display = ('location', 'language', 'voice_name', 'acquisition_channel', 'created_at')
    list_filter = ('language', 'acquisition_channel')
    search_fields = ('location__title',)
    fieldsets = (
        ('Точка', {'fields': ('location', 'language')}),
        ('Сценарии', {'fields': ('short_script', 'long_script')}),
        ('Озвучка', {'fields': (
            'voice_name',
            'audio_short_file',
            'audio_long_file',
            'audio_file',
            'duration_seconds',
        )}),
        ('Происхождение', {'fields': ('source_url', 'acquisition_channel')}),
    )


@admin.register(AudioListenEvent)
class AudioListenEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event_type', 'audio_variant', 'location', 'user', 'completion_percent')
    list_filter = ('event_type', 'audio_variant', 'location')
    search_fields = ('location__title', 'user__username', 'session_id')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_rub', 'is_active')
    list_filter = ('is_active',)


@admin.register(WalkRoute)
class WalkRouteAdmin(admin.ModelAdmin):
    form = WalkRouteAdminForm
    list_display = ('title', 'city', 'district', 'duration_minutes', 'distance_km', 'routing_status', 'is_published')
    list_filter = ('is_published', 'routing_status', 'city', 'interest')
    search_fields = ('title', 'city', 'district')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('routing_provider', 'routing_updated_at', 'route_geometry')
    fieldsets = (
        ('Прогулка', {'fields': ('title', 'slug', 'city', 'district', 'summary')}),
        ('Параметры', {'fields': ('duration_minutes', 'distance_km', 'interest', 'is_published')}),
        ('Пешеходный путь', {'fields': (
            'routing_status',
            'routing_provider',
            'routing_updated_at',
            'route_geometry',
        )}),
    )
    inlines = [RouteStopInline]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')
    search_fields = ('user__username', 'bio')


@admin.register(FavoriteLocation)
class FavoriteLocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'created_at')
    search_fields = ('user__username', 'location__title')
