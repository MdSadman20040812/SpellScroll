from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from apps.auth_core.models import SpellUser
from apps.webtoons.models import Webtoon
from apps.feed.models import FeedCycle, AppOperatingCycle
from vector_store.chroma_client import reset_chroma_collections
# We will import the scraper function when needed

def is_admin_check(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'is_admin_user', False))

def admin_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Match hardcoded settings admin credentials
        expected_user = settings.SPELL_ADMIN_USER
        expected_pass = settings.SPELL_ADMIN_PASSWORD
        
        if username == expected_user and password == expected_pass:
            # Check if user exists in database, else create
            user, created = SpellUser.objects.get_or_create(
                username=username,
                defaults={
                    'email': 'admin@spellscroll.local',
                    'is_staff': True,
                    'is_superuser': True,
                    'is_admin_user': True,
                    'onboarding_complete': True
                }
            )
            if created:
                user.set_password(password)
                user.save()
                
            # Authenticate and login
            auth_user = authenticate(request, username=username, password=password)
            if auth_user:
                login(request, auth_user)
                return redirect('admin_dashboard')
                
        messages.error(request, "Invalid admin credentials.")
        return render(request, 'admin_login.html')
        
    return render(request, 'admin_login.html')

@user_passes_test(is_admin_check, login_url='admin_login')
def admin_dashboard_view(request):
    users = SpellUser.objects.all().order_by('-created_at')
    webtoons = Webtoon.objects.all().order_by('popularity_rank')[:50]
    cycles = FeedCycle.objects.all().order_by('-created_at')
    op_cycles = AppOperatingCycle.objects.all().order_by('-timestamp')[:20]
    
    context = {
        'users': users,
        'webtoons': webtoons,
        'cycles': cycles,
        'op_cycles': op_cycles,
    }
    return render(request, 'admin_dashboard.html', context)

@user_passes_test(is_admin_check, login_url='admin_login')
def admin_reset_chroma_view(request):
    if request.method == 'POST':
        try:
            reset_chroma_collections()
            messages.success(request, "ChromaDB collections cleared successfully.")
        except Exception as e:
            messages.error(request, f"Error clearing ChromaDB: {e}")
    return redirect('admin_dashboard')

@user_passes_test(is_admin_check, login_url='admin_login')
def admin_trigger_scrape_view(request):
    if request.method == 'POST':
        # Simulate running webtoon_scraper_node locally in sync
        from agents.nodes.webtoon_scraper import scrape_and_update_universe
        try:
            count = scrape_and_update_universe()
            messages.success(request, f"Scraped and cataloged {count} new colourful webtoons.")
        except Exception as e:
            messages.error(request, f"Scraping error: {e}")
    return redirect('admin_dashboard')

@user_passes_test(is_admin_check, login_url='admin_login')
def admin_edit_webtoon_view(request, pk):
    webtoon = get_object_or_404(Webtoon, pk=pk)
    if request.method == 'POST':
        webtoon.title = request.POST.get('title', webtoon.title)
        genres_raw = request.POST.get('genres', '')
        webtoon.genres = [g.strip() for g in genres_raw.split(',') if g.strip()]
        try:
            webtoon.colour_rating = float(request.POST.get('colour_rating', webtoon.colour_rating))
        except ValueError:
            pass
        webtoon.synopsis_200w = request.POST.get('synopsis', webtoon.synopsis_200w)
        webtoon.is_active = request.POST.get('is_active') == 'on'
        webtoon.save()
        messages.success(request, f"Webtoon '{webtoon.title}' updated successfully.")
        return redirect('admin_dashboard')
        
    context = {'webtoon': webtoon}
    return render(request, 'admin_edit_webtoon.html', context)
