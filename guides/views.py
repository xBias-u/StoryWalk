import json

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView, CreateView, UpdateView

from .forms import SignUpForm, UserProfileForm
from .models import Location, SubscriptionPlan, FavoriteLocation, UserProfile, AudioListenEvent


class HomeView(TemplateView):
    template_name = 'guides/home.html'


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('location_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        UserProfile.objects.get_or_create(user=self.object)
        login(self.request, self.object)
        return response


class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = 'guides/location_list.html'
    context_object_name = 'locations'

    def get_queryset(self):
        qs = super().get_queryset()
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
        fav_ids = set(FavoriteLocation.objects.filter(user=self.request.user).values_list('location_id', flat=True))
        ctx['favorite_ids'] = fav_ids
        return ctx


class LocationDetailView(LoginRequiredMixin, DetailView):
    model = Location
    template_name = 'guides/location_detail.html'
    context_object_name = 'location'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_favorite'] = FavoriteLocation.objects.filter(user=self.request.user, location=self.object).exists()
        return ctx


class ToggleFavoriteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        location = get_object_or_404(Location, pk=pk)
        fav, created = FavoriteLocation.objects.get_or_create(user=request.user, location=location)
        if not created:
            fav.delete()
        return redirect(request.META.get('HTTP_REFERER', reverse_lazy('location_detail', kwargs={'pk': pk})))


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


class SubscriptionDemoView(LoginRequiredMixin, TemplateView):
    template_name = 'guides/subscription_demo.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = SubscriptionPlan.objects.all()
        return context


class MetricsView(LoginRequiredMixin, TemplateView):
    template_name = 'guides/metrics.html'

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
                avg_completion=Avg('listen_events__completion_percent'),
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


class AudioEventApiView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)

        location_id = data.get('location_id')
        event_type = data.get('event_type')
        current = float(data.get('current_seconds', 0) or 0)
        duration = float(data.get('duration_seconds', 0) or 0)
        completion = float(data.get('completion_percent', 0) or 0)

        if event_type not in {'start', 'progress', 'complete'}:
            return JsonResponse({'ok': False, 'error': 'invalid_event_type'}, status=400)

        location = get_object_or_404(Location, pk=location_id)
        AudioListenEvent.objects.create(
            user=request.user,
            location=location,
            event_type=event_type,
            current_seconds=current,
            duration_seconds=duration,
            completion_percent=completion,
        )
        return JsonResponse({'ok': True})
