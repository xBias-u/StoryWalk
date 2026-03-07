from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, TemplateView

from .models import Location, SubscriptionPlan


class HomeView(TemplateView):
    template_name = 'guides/home.html'


class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = 'guides/location_list.html'
    context_object_name = 'locations'


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
