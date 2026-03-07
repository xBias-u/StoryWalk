from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView, CreateView, UpdateView

from .forms import SignUpForm, UserProfileForm
from .models import Location, SubscriptionPlan, FavoriteLocation, UserProfile


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
