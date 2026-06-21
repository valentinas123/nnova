from pathlib import Path
import mimetypes
import os
import dj_database_url

mimetypes.add_type("text/css", ".css", True)
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔑 SECRET KEY
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-fallback-key-change-me"
)

# 🚀 DETECCIÓN DE ENTORNO
IS_RAILWAY = bool(os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PORT'))
DEBUG = not IS_RAILWAY

ALLOWED_HOSTS = [
    "web-production-41465.up.railway.app",
    "localhost",
    "127.0.0.1",
]

# 📦 APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'usuarios',
    'cursos',
]

# ⚙️ MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nnova.urls'

# 🎨 TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'nnova.wsgi.application'

# 🗄 DATABASE
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
    )
}

# 👤 AUTH
AUTH_USER_MODEL = 'usuarios.Usuario'
LOGIN_REDIRECT_URL = '/app/'
LOGIN_URL = '/login/'

# 📁 STATIC
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# 🔥 STORAGES
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# 📂 MEDIA
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
os.makedirs(MEDIA_ROOT, exist_ok=True)

# 📧 EMAIL CONFIG (SEGURO + RAILWAY READY)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")

# 🔒 SECURITY (RAILWAY PROXIED)
CSRF_TRUSTED_ORIGINS = [
    "https://web-production-41465.up.railway.app"
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = IS_RAILWAY
CSRF_COOKIE_SECURE = IS_RAILWAY

# 🧠 CRÍTICO: Desactivamos la redirección interna de Django para evitar bucles en Railway
SECURE_SSL_REDIRECT = False
