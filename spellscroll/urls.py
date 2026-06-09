from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Built-in Django Admin
    path('admin/', admin.site.urls),
    
    # Custom Application URLs
    path('', include('apps.auth_core.urls')),
    path('', include('apps.feed.urls')),
    path('', include('apps.webtoons.urls')),
    path('admin-spell/', include('apps.admin_panel.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
