"""Path-level authorisation.

Kept deliberately small: it decides which URL prefixes are public, which need
a session, and which need an admin.  View-level ``@login_required`` still does
the real work for individual views; this exists so a newly added private view
cannot be reached by accident.
"""
from django.shortcuts import redirect
from django.urls import reverse

# Reachable without signing in.  Browsing the archive and viewing a series is
# intentionally public - the landing page links straight into it, and covers
# must be fetchable by the browser before any session exists.
PUBLIC_PREFIXES = (
    "/static/",
    "/media/",
    "/cover/",
    "/api/v1/",  # FastAPI validates its own JWT
    "/genres/",
    "/webtoon/",
    "/admin-spell/login/",
    "/admin/",  # Django's own admin has its own auth
)

PUBLIC_PATHS = ("/", "/login/", "/register/", "/logout/", "/offline/")

# Prefixes a signed-in, non-admin user may reach.
MEMBER_PREFIXES = (
    "/feed",
    "/profile",
    "/genres",
    "/archive",   # live provider search + on-demand import
    "/webtoon",
    "/cover",
    "/onboarding",
    "/logout",
)


class SpellAuthZMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return self.get_response(request)

        if not request.user.is_authenticated:
            # Preserve where they were headed so login can return them there.
            return redirect("{0}?next={1}".format(reverse("landing"), path))

        if request.user.is_superuser or getattr(request.user, "is_admin_user", False):
            return self.get_response(request)

        if not path.startswith(MEMBER_PREFIXES):
            return redirect("feed_home")

        return self.get_response(request)
