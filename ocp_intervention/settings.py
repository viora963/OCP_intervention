"""
Django settings for ocp_intervention project.

SÉCURITÉ — variables d'environnement obligatoires en production
-----------------------------------------------------------------
DEBUG=False
SECRET_KEY=<clé générée, jamais celle par défaut>
ALLOWED_HOSTS=exemple.ocpgroup.ma,10.x.x.x
Voir .env.example fourni à côté de ce fichier.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ───────────────────────────────────────────────
# Cœur sécurité : SECRET_KEY / DEBUG / ALLOWED_HOSTS
# ───────────────────────────────────────────────
# DEBUG est False par défaut : en cas d'oubli de configuration, l'app
# démarre en mode sûr plutôt qu'en mode "affiche tout" (stack traces,
# variables d'environnement, requêtes SQL) à n'importe quel visiteur.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Pas de valeur par défaut pour SECRET_KEY : si elle n'est pas définie,
# on refuse de démarrer plutôt que d'utiliser une clé connue de tous
# ceux qui ont accès à ce dépôt.
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        # Autorisé uniquement en dev local pour ne pas bloquer l'onboarding.
        SECRET_KEY = 'django-insecure-dev-only-never-use-in-production'
    else:
        raise Exception(
            "SECRET_KEY doit être définie en variable d'environnement en production. "
            "Générez-en une avec : python -c \"from django.core.management.utils "
            "import get_random_secret_key; print(get_random_secret_key())\""
        )

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()
]
if not DEBUG and not ALLOWED_HOSTS:
    raise Exception("ALLOWED_HOSTS doit être définie en production (liste séparée par des virgules).")
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['*']  # confort en dev local uniquement

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'axes',            # protection brute-force sur le login
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'axes.middleware.AxesMiddleware',   # juste après SecurityMiddleware/sessions
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',   # doit être en premier
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'ocp_intervention.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.user_role',
            ],
        },
    },
]

WSGI_APPLICATION = 'ocp_intervention.wsgi.application'

# ───────────────────────────────────────────────
# Base de données
# ───────────────────────────────────────────────
# SQLite convient au développement. En production, passez à PostgreSQL
# (fichier unique sur disque = risque de fuite complète en cas de mauvaise
# config du serveur web ou d'accès filesystem non prévu).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ───────────────────────────────────────────────
# Mots de passe
# ───────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Casablanca'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Email backend for development (prints to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ───────────────────────────────────────────────
# Sessions
# ───────────────────────────────────────────────
SESSION_COOKIE_AGE = 86400  # 24 heures
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True   # cookie de session inaccessible en JS

# ───────────────────────────────────────────────
# django-axes : verrouillage après tentatives de login échouées
# ───────────────────────────────────────────────
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # heure(s)
AXES_LOCKOUT_PARAMETERS = ['username']  # verrouille par compte, pas par IP seule

# ───────────────────────────────────────────────
# En-têtes / cookies de sécurité — actifs uniquement quand DEBUG=False
# (pour ne pas casser le dev local en HTTP sans certificat)
# ───────────────────────────────────────────────
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True

    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = 'DENY'

# ───────────────────────────────────────────────
# Logging sécurité
# ───────────────────────────────────────────────
(BASE_DIR / 'logs').mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['console', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'axes': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}