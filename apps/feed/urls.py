from django.urls import path
from . import views

urlpatterns = [
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('feed/', views.feed_home_view, name='feed_home'),
    path('profile/', views.profile_view, name='profile'),
]
