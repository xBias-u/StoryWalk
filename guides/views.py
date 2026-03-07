from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, TemplateView, CreateView

from .forms import SignUpForm
from .models import Location, SubscriptionPlan


class HomeView(TemplateView):
    template_name = 'guides/home.html'


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('location_list')

    def form_valid(self, form):
        response = super().form_valid(form)
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
        return ctx


class LocationDetailView(LoginRequiredMixin, DetailView):
    model = Location
    template_name = 'guides/location_detail.html'
    context_object_name = 'location'


class SubscriptionDemoView(LoginRequiredMixin, TemplateView):
    template_name = 'guides/subscription_demo.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = SubscriptionPlan.objects.all()
        return context
