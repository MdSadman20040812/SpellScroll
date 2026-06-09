import jwt
import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.conf import settings
from .models import SpellUser

def generate_jwt_token(user):
    payload = {
        'user_id': str(user.id),
        'username': user.username,
        'is_admin': user.is_superuser or getattr(user, 'is_admin_user', False),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def landing_view(request):
    if request.user.is_authenticated:
        if request.user.onboarding_complete:
            return redirect('feed_home')
        return redirect('onboarding')
    return render(request, 'landing.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        display_name = request.POST.get('display_name', username)
        
        if not username or not email or not password:
            messages.error(request, "All fields are required.")
            return redirect('landing')
            
        if SpellUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('landing')
            
        user = SpellUser.objects.create_user(
            username=username, 
            email=email, 
            password=password,
            display_name=display_name
        )
        login(request, user)
        
        # Issue JWT and store in session / cookie
        token = generate_jwt_token(user)
        request.session['jwt_token'] = token
        
        response = redirect('onboarding')
        response.set_cookie('access_token', token, httponly=True, samesite='Lax')
        return response
        
    return redirect('landing')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            token = generate_jwt_token(user)
            request.session['jwt_token'] = token
            
            target = 'feed_home' if user.onboarding_complete else 'onboarding'
            response = redirect(target)
            response.set_cookie('access_token', token, httponly=True, samesite='Lax')
            return response
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('landing')
            
    return redirect('landing')

def logout_view(request):
    logout(request)
    response = redirect('landing')
    response.delete_cookie('access_token')
    return response
