import requests
from django.shortcuts import render, get_object_or_404
from django.db.models import Count
from .models import Webtoon, UserWebtoonStatus

def get_mangadex_chapters(mangadex_id):
    """
    Utility function to retrieve latest chapters for a webtoon from MangaDex API.
    """
    if not mangadex_id or mangadex_id == 'mock':
        return []
    try:
        url = f"https://api.mangadex.org/manga/{mangadex_id}/feed"
        params = {
            "limit": 5,
            "order[chapter]": "desc",
            "translatedLanguage[]": ["en"]
        }
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            chapters = []
            for item in data:
                attrs = item.get('attributes', {})
                chapters.append({
                    'id': item.get('id'),
                    'title': attrs.get('title') or f"Chapter {attrs.get('chapter', '?')}",
                    'chapter': attrs.get('chapter'),
                    'external_url': f"https://mangadex.org/chapter/{item.get('id')}"
                })
            return chapters
    except Exception as e:
        print(f"MangaDex feed fetch error: {e}")
    return []

def webtoon_detail_view(request, slug):
    webtoon = get_object_or_404(Webtoon, slug=slug)
    user_status = None
    if request.user.is_authenticated:
        user_status = UserWebtoonStatus.objects.filter(user=request.user, webtoon=webtoon).first()
        
    chapters = get_mangadex_chapters(webtoon.mangadex_id)
    
    # If no real chapters, provide mock preview chapters for discovery experience
    if not chapters:
        chapters = [
            {'title': 'Chapter 1: The Awakening', 'external_url': '#', 'chapter': '1'},
            {'title': 'Chapter 2: Magic Unleashed', 'external_url': '#', 'chapter': '2'},
            {'title': 'Chapter 3: Scroll of Truth', 'external_url': '#', 'chapter': '3'},
        ]
        
    context = {
        'webtoon': webtoon,
        'user_status': user_status,
        'chapters': chapters
    }
    return render(request, 'webtoon_detail.html', context)

def genre_list_view(request):
    # Retrieve all webtoons and extract unique genres
    webtoons = Webtoon.objects.filter(is_active=True)
    genres_count = {}
    for webtoon in webtoons:
        genres = webtoon.genres if isinstance(webtoon.genres, list) else []
        for genre in genres:
            genre_clean = genre.strip().capitalize()
            genres_count[genre_clean] = genres_count.get(genre_clean, 0) + 1
            
    genres_list = [{'name': g, 'count': c} for g, c in genres_count.items()]
    genres_list = sorted(genres_list, key=lambda x: x['count'], reverse=True)
    
    context = {
        'genres': genres_list
    }
    return render(request, 'genres.html', context)
