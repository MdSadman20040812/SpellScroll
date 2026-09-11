from django.urls import path

from . import views

urlpatterns = [
    path("webtoon/<slug:slug>/", views.webtoon_detail_view, name="webtoon_detail"),
    path("genres/", views.genre_list_view, name="genre_list"),
    path("archive/import/", views.import_webtoon_view, name="import_webtoon"),
    # Cover proxy: always-renderable artwork on our own origin.
    path("cover/<uuid:webtoon_id>/", views.webtoon_cover_view, name="webtoon_cover"),
    path("cover/<uuid:webtoon_id>/banner/", views.webtoon_banner_view, name="webtoon_banner"),
]
