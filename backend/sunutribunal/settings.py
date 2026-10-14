"""
SunuTribunal — Django Settings
Backend: Django 4.2 + DRF + JWT + PostgreSQL
"""
import environ
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')


SECRET_KEY = env('SECRET_KEY', default='django-insecure-sunutribunal-change-in-production')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '10.20.3.214',
    'suffering-zestfully-treason.ngrok-free.dev',
    '.ngrok-free.dev',     # tout domaine ngrok (si le lien change)
    '.ngrok-free.app',
    '.up.railway.app',     # déploiement Railway (après la soutenance)
]
# ── Applications ───────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
]
LOCAL_APPS = [
    'apps.accounts',
    'apps.rdv',
    'apps.plaintes',
    'apps.alertes',
    'apps.notifications',
    'apps.registres',      # Registres courrier arrivée / départ + transmission
    'apps.archives',       # Archivage numérique des dossiers
    'apps.correspondances',  # Courriers citoyen <-> tribunal (inscrits au registre)
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sunutribunal.urls'
AUTH_USER_MODEL = 'accounts.User'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'sunutribunal.wsgi.application'

# ── Database — PostgreSQL ──────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ── Auth ───────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

# Tests uniquement : hachage rapide des mots de passe (la suite passe de ~3 min à quelques secondes)
import sys
if 'test' in sys.argv:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# ── REST Framework ─────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # JWT + blocage tant que le mot de passe temporaire n'a pas été changé
        'apps.accounts.authentication.JWTAuthentificationSecurisee',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Limites d'usage des assistants juridiques (apps/chatbot/throttles.py)
    'DEFAULT_THROTTLE_RATES': {
        'assistant_ip':        '20/minute',
        'assistant_greffe':    '20/minute',
        'generation_document': '30/hour',
    },
}

# ── JWT ────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,
    'AUTH_HEADER_TYPES':      ('Bearer',),
}

# ── CORS ───────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://suffering-zestfully-treason.ngrok-free.dev',
]
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'ngrok-skip-browser-warning',
]

# ngrok / Railway transmettent la requête en http : on garde https dans les liens
# des fichiers (pièces scannées), sinon l'APK les bloque (contenu mixte)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── Static & Media ─────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Internationalisation ───────────────────
LANGUAGE_CODE = 'fr-sn'
TIME_ZONE     = 'Africa/Dakar'
USE_I18N      = True
USE_TZ        = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Redis / Celery ─────────────────────────
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# ── Firebase (notifications push) ──────────
FIREBASE_CREDENTIALS = env('FIREBASE_CREDENTIALS', default='')

# ── Twilio (SMS) ───────────────────────────
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN  = env('TWILIO_AUTH_TOKEN',  default='')
TWILIO_FROM_NUMBER = env('TWILIO_FROM_NUMBER', default='')
# SMS par Brevo (prioritaire sur Twilio) : BREVO_API_KEY (plus bas) + nom d'expéditeur, 11 caractères max
BREVO_SMS_SENDER   = env('BREVO_SMS_SENDER', default='')
# SMS gratuits par votre téléphone Android (application « SMS Gateway for Android », sms-gate.app) :
# prioritaire sur Brevo et Twilio. Identifiants affichés dans l'application (mode « Cloud server »).
SMSGATE_URL      = env('SMSGATE_URL', default='https://api.sms-gate.app/3rdparty/v1/message')
SMSGATE_LOGIN    = env('SMSGATE_LOGIN', default='')
SMSGATE_PASSWORD = env('SMSGATE_PASSWORD', default='')

# ── Email (identifiants provisoires du personnel) ──
# Gmail : EMAIL_HOST_PASSWORD = « mot de passe d'application » (compte Google → Sécurité),
# pas le mot de passe habituel. Sans EMAIL_HOST_USER, l'e-mail s'affiche dans le terminal.
EMAIL_HOST          = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT          = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS       = env.bool('EMAIL_USE_TLS', default=True)    # port 587 (STARTTLS)
EMAIL_USE_SSL       = env.bool('EMAIL_USE_SSL', default=False)   # port 465 (SSL direct) — jamais les deux à True
EMAIL_HOST_USER     = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_TIMEOUT       = 20
# Brevo (API web, port 443) : prioritaire quand la clé est renseignée — passe là où le SMTP est bloqué
BREVO_API_KEY       = env('BREVO_API_KEY', default='')
if BREVO_API_KEY:
    EMAIL_BACKEND = 'apps.accounts.brevo.BrevoEmailBackend'
elif EMAIL_HOST_USER:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL  = env('DEFAULT_FROM_EMAIL',
                          default=f'SunuTribunal <{EMAIL_HOST_USER or "noreply@sunutribunal.sn"}>')
# Adresse de la plateforme mise dans les e-mails (bouton « Accéder à SunuTribunal »)
FRONTEND_URL = env('FRONTEND_URL', default='')

GROQ_API_KEY = env('GROQ_API_KEY', default='')

# ── Numérotation des registres ─────────────
# Code utilisé si l'agent n'est rattaché à aucun tribunal (ex. CA-00001/2026/SNTRIB)
CODE_JURIDICTION = env('CODE_JURIDICTION', default='SNTRIB')

# ── Fichiers envoyés (scans) ───────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024   # 20 Mo
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

