from django.urls import path
from . import views

urlpatterns = [
    path('webtoon/<slug:slug>/', views.webtoon_detail_view, name='webtoon_detail'),
    path('genres/', views.genre_list_view, name='genre_list'),
]
