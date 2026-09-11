import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-for-development')
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'daphne',  # required for channels ASGI
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'channels',
    'apps.auth_core',
    'apps.webtoons',
    'apps.feed',
    'apps.admin_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Serves /static/ under any ASGI server. Django only auto-serves static
    # files through `runserver`, so without this the app has no CSS when run
    # under uvicorn/daphne - which is how the unified ASGI app is deployed.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.auth_core.middleware.SpellAuthZMiddleware',  # Custom AuthZ middleware
]

ROOT_URLCONF = 'spellscroll.urls'

# Django >= 4.1 wraps template loading in the cached loader even when DEBUG is
# on; `runserver` hides that by restarting the process on every edit. This app
# is served by uvicorn/daphne (the unified ASGI entry point), where nothing
# restarts, so template edits were silently ignored until the server was
# bounced. Selecting the loaders explicitly restores per-request reloading in
# development while keeping the cached loader in production.
_TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        # APP_DIRS must stay unset when OPTIONS['loaders'] is given.
        'OPTIONS': {
            'loaders': (
                _TEMPLATE_LOADERS
                if DEBUG
                else [('django.template.loaders.cached.Loader', _TEMPLATE_LOADERS)]
            ),
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'spellscroll.wsgi.application'
ASGI_APPLICATION = 'spellscroll.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom User Model
AUTH_USER_MODEL = 'auth_core.SpellUser'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password Hashers (Argon2 as requested)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise serves STATICFILES_DIRS directly while DEBUG is on, so no
# collectstatic step is needed during development.
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        )
    },
}

# Media files (User preference documents)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Channels / WebSocket configuration
# Using in-memory layer to avoid strict Redis dependencies in local developer environment
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# ---------------------------------------------------------------------------
# LLM provider (optional).
#
# Every supported provider speaks the OpenAI /chat/completions shape, so
# switching is two env vars. All of these have a free tier; see services/llm.py
# for the model defaults. Leave LLM_PROVIDER unset to run entirely on the
# deterministic local ranking, which needs no key and no network.
#
#   LLM_PROVIDER=groq | gemini | openrouter | cerebras | none
#   LLM_API_KEY=...
#   LLM_MODEL=...        (optional override)
# ---------------------------------------------------------------------------
LLM_PROVIDER = os.getenv('LLM_PROVIDER', '')
LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_MODEL = os.getenv('LLM_MODEL', '')

# Back-compat: an existing CEREBRAS_API_KEY keeps working without edits.
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY', '')
if not LLM_PROVIDER and CEREBRAS_API_KEY and CEREBRAS_API_KEY != 'mock_key':
    LLM_PROVIDER = 'cerebras'
    LLM_API_KEY = CEREBRAS_API_KEY
SERPAPI_KEY = os.getenv('SERPAPI_KEY', 'mock_key')
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY', 'mock_key')
MANGADEX_CLIENT_ID = os.getenv('MANGADEX_CLIENT_ID')
MANGADEX_CLIENT_SECRET = os.getenv('MANGADEX_CLIENT_SECRET')

# Admin settings
SPELL_ADMIN_USER = os.getenv('SPELL_ADMIN_USER', 'spellmaster')
SPELL_ADMIN_PASSWORD = os.getenv('SPELL_ADMIN_PASSWORD', 'Scroll@Admin2025!')
CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', os.path.join(BASE_DIR, 'vector_store', 'chroma_data'))
