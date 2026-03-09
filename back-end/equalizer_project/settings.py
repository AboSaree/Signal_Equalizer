"""
Django settings for SignalLab equalizer backend.
Stateless — no database required.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'signallab-dev-key-change-in-production'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'corsheaders',
    'rest_framework',
    'signals',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'equalizer_project.urls'

WSGI_APPLICATION = 'equalizer_project.wsgi.application'

# ── No database ──────────────────────────────────────
DATABASES = {}

# ── CORS ─────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ── Upload limits (50 MB) ────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 52_428_800
FILE_UPLOAD_MAX_MEMORY_SIZE = 52_428_800

# ── DRF ──────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.JSONParser',
    ],
    'UNAUTHENTICATED_USER': None,
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
