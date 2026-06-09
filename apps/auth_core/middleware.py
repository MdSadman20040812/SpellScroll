from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.urls import resolve

class SpellAuthZMiddleware:
    """
    Enforces authorization constraints based on user roles and paths.
    Injects request properties if needed.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        path = request.path
        
        # 1. Allow static/media and root authentication paths
        if (path.startswith('/static/') or 
            path.startswith('/media/') or 
            path.startswith('/api/v1/') or # FastAPI has its own JWT validation
            path in ['/', '/login/', '/register/', '/logout/', '/admin-spell/login/']):
            return self.get_response(request)
            
        # 2. Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('landing')  # Redirect anonymous users to Landing/Register
            
        # 3. Check role authorization rules
        # If user is admin (is_superuser or is_admin_user flag), they can access anything
        if request.user.is_superuser or getattr(request.user, 'is_admin_user', False):
            return self.get_response(request)
            
        # Standard user path whitelist
        permitted_prefixes = ['/feed', '/profile', '/genres', '/webtoons', '/onboarding', '/logout']
        is_permitted = any(path.startswith(prefix) for prefix in permitted_prefixes)
        
        if not is_permitted:
            return HttpResponseForbidden("Access Denied: You do not have permission to access this resource.")
            
        return self.get_response(request)
