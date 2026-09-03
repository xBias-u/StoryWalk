import hashlib
import json
import math
import re
import time
from urllib.parse import urlencode

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Avg, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import ListView, DetailView, TemplateView, CreateView, UpdateView

from .forms import SignUpForm, UserProfileForm
from .models import (
    AudioListenEvent,
    FavoriteLocation,
    Location,
    SubscriptionPlan,
    UserProfile,
    WalkRoute,
)


SESSION_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{8,64}$')
MAX_AUDIO_SECONDS = 24 * 60 * 60


def public_routes():
    return (
        WalkRoute.objects
        .filter(is_published=True, routing_status='verified')
        .exclude(stops__location__is_published=False)
        .annotate(public_stop_count=Count('stops'))
        .filter(public_stop_count__gte=2)
        .distinct()
    )


class HealthCheckView(View):
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except Exception:
            return JsonResponse({'status': 'unavailable'}, status=503)
        return JsonResponse({'status': 'ok'})


class HomeView(TemplateView):
    template_name = 'guides/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_locations'] = Location.objects.filter(is_published=True, is_featured=True)[:3]
        context['featured_route'] = public_routes().first()
        return context


class RouteMatchView(View):
    def get(self, request):
        city = request.GET.get('city', '').strip()
        duration_raw = request.GET.get('duration', '').strip()
        interest = request.GET.get('interest', '').strip()

        routes = list(public_routes())
        if city:
            city_routes = [route for route in routes if city.casefold() in route.city.casefold()]
            routes = city_routes

        if not routes:
            query = urlencode({'city': city, 'duration': duration_raw, 'interest': interest})
            return HttpResponseRedirect(f"{reverse_lazy('location_list')}?{query}")

        try:
            duration = int(duration_raw)
        except (TypeError, ValueError):
            duration = 60

        route = min(
            routes,
            key=lambda item: (
                item.interest != interest if interest else False,
                abs(item.duration_minutes - duration),
            ),
        )
        query = urlencode({'duration': duration, 'interest': interest})
        return HttpResponseRedirect(f"{route.get_absolute_url()}?{query}")


class PublishedRouteMixin:
    model = WalkRoute
    context_object_name = 'route'

    def get_queryset(self):
        routes = WalkRoute.objects.all()
        if not self.request.user.is_staff:
            routes = public_routes()
        return routes.prefetch_related(
            'stops__location__gallery_images',
            'stops__location__audio_guide',
        )


class RoutePreviewView(PublishedRouteMixin, DetailView):
    template_name = 'guides/route_preview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stops = list(self.object.stops.select_related('location').all())
        context['route_stops'] = stops
        context['total_walk_minutes'] = sum(stop.walk_minutes for stop in stops)
        context['route_visualization'] = build_route_visualization(self.object, stops)
        try:
            requested_duration = int(self.request.GET.get('duration', ''))
        except (TypeError, ValueError):
            requested_duration = None
        context['requested_duration'] = requested_duration
        context['duration_adjusted'] = (
            requested_duration is not None and requested_duration != self.object.duration_minutes
        )
        return context


def build_route_visualization(route, stops):
    """Project stored GeoJSON into the calm, map-like route signature card."""
    features = route.route_geometry.get('features', []) if route.route_geometry else []
    raw_paths = []
    for feature in features:
        geometry = feature.get('geometry') or {}
        if geometry.get('type') != 'LineString':
            continue
        coordinates = geometry.get('coordinates') or []
        if len(coordinates) >= 2:
            raw_paths.append(coordinates)
    if not raw_paths:
        return None

    stop_coordinates = [
        [float(stop.location.longitude), float(stop.location.latitude)]
        for stop in stops
        if stop.location.has_coordinates
    ]
    all_coordinates = [point for path in raw_paths for point in path] + stop_coordinates
    if len(all_coordinates) < 2:
        return None

    average_latitude = sum(point[1] for point in all_coordinates) / len(all_coordinates)
    longitude_factor = math.cos(math.radians(average_latitude))
    metric_points = [
        (point[0] * longitude_factor, point[1])
        for point in all_coordinates
    ]
    min_x = min(point[0] for point in metric_points)
    max_x = max(point[0] for point in metric_points)
    min_y = min(point[1] for point in metric_points)
    max_y = max(point[1] for point in metric_points)
    span_x = max(max_x - min_x, 0.000001)
    span_y = max(max_y - min_y, 0.000001)
    scale = min(332 / span_x, 432 / span_y)
    offset_x = (420 - span_x * scale) / 2
    offset_y = (520 - span_y * scale) / 2

    def project(point):
        x = (point[0] * longitude_factor - min_x) * scale + offset_x
        y = (max_y - point[1]) * scale + offset_y
        return round(x, 1), round(y, 1)

    paths = []
    for path in raw_paths:
        projected = [project(point) for point in path]
        paths.append(' '.join(
            ('M' if index == 0 else 'L') + f'{x},{y}'
            for index, (x, y) in enumerate(projected)
        ))

    markers = []
    for stop in stops:
        if not stop.location.has_coordinates:
            continue
        x, y = project([float(stop.location.longitude), float(stop.location.latitude)])
        markers.append({
            'position': stop.position,
            'title': stop.location.title,
            'x': x,
            'y': y,
        })
    return {'paths': paths, 'markers': markers}


@method_decorator(ensure_csrf_cookie, name='dispatch')
class RouteWalkView(PublishedRouteMixin, DetailView):
    template_name = 'guides/route_walk.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stops = list(self.object.stops.select_related('location').all())
        try:
            current_index = int(self.request.GET.get('stop', '1')) - 1
        except (TypeError, ValueError):
            current_index = 0
        current_index = min(max(current_index, 0), max(len(stops) - 1, 0))

        context['route_stops'] = stops
        context['current_stop'] = stops[current_index] if stops else None
        context['previous_stop'] = stops[current_index - 1] if current_index > 0 else None
        context['next_stop'] = stops[current_index + 1] if current_index + 1 < len(stops) else None
        context['current_number'] = current_index + 1
        context['progress_percent'] = round((current_index + 1) / len(stops) * 100) if stops else 0
        return context


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('location_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        UserProfile.objects.get_or_create(user=self.object)
        login(self.request, self.object)
        return response


class LocationListView(ListView):
    model = Location
    template_name = 'guides/location_list.html'
    context_object_name = 'locations'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_published=True)
        q = self.request.GET.get('q', '').strip()
        city = self.request.GET.get('city', '').strip()

        if q:
            qs = qs.filter(title__icontains=q)
        if city:
            qs = qs.filter(city__icontains=city)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '').strip()
        ctx['city'] = self.request.GET.get('city', '').strip()
        ctx['duration'] = self.request.GET.get('duration', '').strip()
        ctx['interest'] = self.request.GET.get('interest', '').strip()
        ctx['interest_label'] = {
            'architecture': 'Архитектура',
            'history': 'История',
            'art': 'Искусство',
            'local': 'Городские истории',
        }.get(ctx['interest'], '')
        fav_ids = set()
        if self.request.user.is_authenticated:
            fav_ids = set(
                FavoriteLocation.objects.filter(user=self.request.user).values_list('location_id', flat=True)
            )
        ctx['favorite_ids'] = fav_ids
        return ctx


@method_decorator(ensure_csrf_cookie, name='dispatch')
class LocationDetailView(DetailView):
    model = Location
    template_name = 'guides/location_detail.html'
    context_object_name = 'location'

    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_favorite'] = False
        if self.request.user.is_authenticated:
            ctx['is_favorite'] = FavoriteLocation.objects.filter(
                user=self.request.user,
                location=self.object,
            ).exists()
        return ctx


class ToggleFavoriteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        location = get_object_or_404(Location, pk=pk, is_published=True)
        fav, created = FavoriteLocation.objects.get_or_create(user=request.user, location=location)
        if not created:
            fav.delete()
        fallback = reverse_lazy('location_detail', kwargs={'pk': pk})
        referer = request.META.get('HTTP_REFERER', '')
        if not url_has_allowed_host_and_scheme(
            referer,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            referer = fallback
        return redirect(referer)


class ProfileView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'guides/profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        obj, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['favorites'] = Location.objects.filter(liked_by__user=self.request.user)
        return ctx


class PlansView(LoginRequiredMixin, TemplateView):
    template_name = 'guides/plans.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = SubscriptionPlan.objects.filter(is_active=True)
        return context


class MetricsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'guides/metrics.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        total_starts = AudioListenEvent.objects.filter(event_type='start').count()
        total_completes = AudioListenEvent.objects.filter(event_type='complete').count()
        avg_completion = AudioListenEvent.objects.filter(event_type__in=['progress', 'complete']).aggregate(
            avg=Avg('completion_percent')
        )['avg'] or 0

        per_location = (
            Location.objects.annotate(
                starts=Count('listen_events', filter=Q(listen_events__event_type='start')),
                completes=Count('listen_events', filter=Q(listen_events__event_type='complete')),
                avg_completion=Avg(
                    'listen_events__completion_percent',
                    filter=Q(listen_events__event_type__in=['progress', 'complete']),
                ),
            )
            .order_by('-starts', 'title')
        )

        ctx.update({
            'total_starts': total_starts,
            'total_completes': total_completes,
            'avg_completion': round(avg_completion, 1),
            'completion_rate': round((total_completes / total_starts * 100), 1) if total_starts else 0,
            'per_location': per_location,
        })
        return ctx


class AudioEventApiView(View):
    def post(self, request):
        if len(request.body) > 4_096:
            return JsonResponse({'ok': False, 'error': 'payload_too_large'}, status=413)
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)

        if not isinstance(data, dict):
            return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)

        try:
            location_id = int(data.get('location_id'))
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'invalid_location_id'}, status=400)
        event_type = data.get('event_type')
        session_id = str(data.get('session_id', ''))
        audio_variant = data.get('audio_variant', 'legacy')

        if event_type not in {'start', 'progress', 'complete'}:
            return JsonResponse({'ok': False, 'error': 'invalid_event_type'}, status=400)
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            return JsonResponse({'ok': False, 'error': 'invalid_session_id'}, status=400)
        if audio_variant not in {'short', 'long', 'route', 'legacy'}:
            return JsonResponse({'ok': False, 'error': 'invalid_audio_variant'}, status=400)

        try:
            current = self._finite_number(data.get('current_seconds', 0))
            duration = self._finite_number(data.get('duration_seconds', 0))
            completion = self._finite_number(data.get('completion_percent', 0))
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'invalid_measurement'}, status=400)

        if not 0 <= current <= MAX_AUDIO_SECONDS or not 0 <= duration <= MAX_AUDIO_SECONDS:
            return JsonResponse({'ok': False, 'error': 'invalid_measurement'}, status=400)
        if not 0 <= completion <= 100:
            return JsonResponse({'ok': False, 'error': 'invalid_measurement'}, status=400)
        if duration and current > duration + 1:
            return JsonResponse({'ok': False, 'error': 'invalid_measurement'}, status=400)
        if self._rate_limited(request):
            return JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)

        location = get_object_or_404(Location, pk=location_id, is_published=True)

        dedupe_material = f'{session_id}:{location_id}:{audio_variant}:{event_type}:{round(current / 5)}'
        dedupe_key = 'audio-event:' + hashlib.sha256(dedupe_material.encode()).hexdigest()
        if not cache.add(dedupe_key, True, timeout=8):
            return JsonResponse({'ok': True, 'duplicate': True})

        AudioListenEvent.objects.create(
            user=request.user if request.user.is_authenticated else None,
            location=location,
            event_type=event_type,
            session_id=session_id,
            audio_variant=audio_variant,
            current_seconds=current,
            duration_seconds=duration,
            completion_percent=completion,
        )
        return JsonResponse({'ok': True})

    @staticmethod
    def _finite_number(value):
        number = float(value or 0)
        if not math.isfinite(number):
            raise ValueError('measurement must be finite')
        return number

    @staticmethod
    def _rate_limited(request):
        remote_address = request.META.get('REMOTE_ADDR', 'unknown')
        identity = hashlib.sha256(remote_address.encode()).hexdigest()[:20]
        bucket = int(time.time() // 60)
        key = f'audio-event-rate:{identity}:{bucket}'
        if cache.add(key, 1, timeout=70):
            return False
        try:
            return cache.incr(key) > 120
        except ValueError:
            return False
