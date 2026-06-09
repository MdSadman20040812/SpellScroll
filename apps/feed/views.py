import os
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from apps.webtoons.models import UserWebtoonStatus, Webtoon

@login_required
def onboarding_view(request):
    if request.user.onboarding_complete:
        return redirect('feed_home')
    return render(request, 'onboarding.html')

@login_required
def feed_home_view(request):
    if not request.user.onboarding_complete:
        return redirect('onboarding')
        
    # Get user token to pass to the template for API endpoints access
    jwt_token = request.session.get('jwt_token', '')
    
    # Extract existing statuses to pre-load rating and status state
    statuses = UserWebtoonStatus.objects.filter(user=request.user)
    statuses_dict = {str(status.webtoon.id): status.status for status in statuses}
    
    context = {
        'jwt_token': jwt_token,
        'statuses_dict_json': json.dumps(statuses_dict),
    }
    return render(request, 'feed.html', context)

@login_required
def profile_view(request):
    user_id = str(request.user.id)
    pref_path = os.path.join(settings.MEDIA_ROOT, 'users', user_id, 'preferences.json')
    
    preferences = {}
    if os.path.exists(pref_path):
        try:
            with open(pref_path, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
        except Exception as e:
            print(f"Error loading preference file: {e}")
            
    # Compile stats for radar chart based on UserWebtoonStatus
    user_statuses = UserWebtoonStatus.objects.filter(user=request.user)
    completed_count = user_statuses.filter(status='completed').count()
    reading_count = user_statuses.filter(status='reading').count()
    skipped_count = user_statuses.filter(status='skipped').count()
    
    # Calculate genre affinity
    genre_affinity = {}
    for us in user_statuses:
        # Increase score for completed/reading, decrease or neutral for skipped
        weight = 2 if us.status in ['completed', 'reading'] else -1
        genres = us.webtoon.genres if isinstance(us.webtoon.genres, list) else []
        for genre in genres:
            genre_affinity[genre] = genre_affinity.get(genre, 0) + weight
            
    # Sort and slice top 5 genres for chart
    sorted_genres = sorted(genre_affinity.items(), key=lambda x: x[1], reverse=True)[:5]
    chart_labels = [g[0] for g in sorted_genres]
    chart_data = [max(0, g[1]) for g in sorted_genres]
    
    # Fallbacks if chart labels empty
    if not chart_labels:
        chart_labels = ['Action', 'Fantasy', 'Romance', 'Comedy', 'Drama']
        chart_data = [0, 0, 0, 0, 0]
        
    context = {
        'preferences': preferences,
        'completed_count': completed_count,
        'reading_count': reading_count,
        'skipped_count': skipped_count,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data)
    }
    return render(request, 'profile.html', context)
