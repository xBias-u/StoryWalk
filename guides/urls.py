from django.urls import path
from .views import (
    HomeView,
    LocationListView,
    LocationDetailView,
    PlansView,
    SignUpView,
    ToggleFavoriteView,
    ProfileView,
    MetricsView,
    AudioEventApiView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('guides/', LocationListView.as_view(), name='location_list'),
    path('guides/<int:pk>/', LocationDetailView.as_view(), name='location_detail'),
    path('guides/<int:pk>/favorite/', ToggleFavoriteView.as_view(), name='toggle_favorite'),
    path('plans/', PlansView.as_view(), name='plans'),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('metrics/', MetricsView.as_view(), name='metrics'),
    path('api/audio-events/', AudioEventApiView.as_view(), name='audio_event_api'),
]
