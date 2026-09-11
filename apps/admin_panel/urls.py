from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login_view, name='admin_login'),
    path('', views.admin_dashboard_view, name='admin_dashboard'),
    path('reset-chroma/', views.admin_reset_chroma_view, name='admin_reset_chroma'),
    path('trigger-scrape/', views.admin_trigger_scrape_view, name='admin_trigger_scrape'),
    path('resync-covers/', views.admin_resync_covers_view, name='admin_resync_covers'),
    path('edit-webtoon/<uuid:pk>/', views.admin_edit_webtoon_view, name='admin_edit_webtoon'),
]
