from django.urls import path
from .views import HomeView, LocationListView, LocationDetailView, SubscriptionDemoView, SignUpView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('guides/', LocationListView.as_view(), name='location_list'),
    path('guides/<int:pk>/', LocationDetailView.as_view(), name='location_detail'),
    path('subscription-demo/', SubscriptionDemoView.as_view(), name='subscription_demo'),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),
]
