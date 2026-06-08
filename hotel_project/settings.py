"""
Django settings for Aero Luxe Select project.
Multi-site luxury car rental & airport transfer system.

Developed by GABOOM | Tel: 829 509 84 12
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-aeroluxe-dev-key-change-in-production-2024'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Project apps
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom multi-site middleware
    'core.middleware.SiteMiddleware',
]

ROOT_URLCONF = 'hotel_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'core' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'core.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'hotel_project.wsgi.application'


import dj_database_url

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'en'

LANGUAGES = [
    ('en', 'English'),
    ('es', 'Español'),
]

TIME_ZONE = 'America/New_York'

USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==========================================================================
# AERO LUXE SELECT CONFIGURATION
# ==========================================================================

# Multi-site configuration
# Maps domain names to site slugs for production
SITE_DOMAIN_MAP = {
    'aeroluxeselect-nyc.com': 'nyc',
    'www.aeroluxeselect-nyc.com': 'nyc',
    'aeroluxeselect-dr.com': 'dr',
    'www.aeroluxeselect-dr.com': 'dr',
    'localhost': 'nyc',  # Default for development
    '127.0.0.1': 'nyc',
}

# Default site slug if none detected
DEFAULT_SITE_SLUG = 'nyc'

# Site-language mapping
SITE_LANGUAGES = {
    'nyc': ['en'],
    'dr': ['en', 'es'],
}


# ==========================================================================
# STRIPE CONFIGURATION (Configurable from dashboard)
# ==========================================================================
# These are fallback values - actual keys are stored in SiteSettings model
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')


# ==========================================================================
# BUSINESS LOGIC CONFIGURATION
# ==========================================================================

# Platform commission rates (for Viator/Expedia bookings)
PLATFORM_COMMISSION_RATES = {
    'VIATOR': 0.25,   # 25% markup
    'EXPEDIA': 0.20,  # 20% markup
    'OTHER': 0.20,    # 20% default
}

# Hourly service minimums
HOURLY_MIN_HOURS = 3
HOURLY_RATE_RANGE = {
    'min': 65,
    'max': 90,
}


# ==========================================================================
# DEVELOPER CREDIT
# ==========================================================================
DEVELOPER_NAME = 'GABOOM'
DEVELOPER_PHONE = '829 509 84 12'
COMPANY_NAME = 'Aero Luxe Select'
