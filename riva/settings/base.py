"""
Riva Veteriner Otomasyon — temel ayarlar.

Ortam (dev/prod) ayrımı için `dev.py` / `prod.py` bu dosyayı genişletir.
Tüm sırlar ve ortam-bağımlı değerler `.env` üzerinden gelir (django-environ).
"""

from pathlib import Path

import environ

# riva/settings/base.py -> proje kökü 3 seviye yukarıda
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
)

# .env varsa oku (lokal geliştirme). Prod'da gerçek ortam değişkenleri kullanılır.
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    environ.Env.read_env(_env_file)

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")


# ---------------------------------------------------------------------------
# Uygulamalar
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

# Sıralama önemli: accounts (custom user) önce gelmeli.
LOCAL_APPS = [
    "apps.accounts",
    "apps.core",
    "apps.owners",
    "apps.patients",
    "apps.appointments",
    "apps.medical",
    "apps.vaccines",
    "apps.reminders",
    "apps.billing",
    "apps.files",
    "apps.reports",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "riva.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.clinic",
            ],
        },
    },
]

WSGI_APPLICATION = "riva.wsgi.application"


# ---------------------------------------------------------------------------
# Veritabanı (PostgreSQL)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://riva:riva@localhost:5432/riva",
    )
}


# ---------------------------------------------------------------------------
# Parola doğrulama
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Yerelleştirme — Türkçe arayüz, İstanbul saat dilimi
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Statik & medya dosyaları
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Dosya depolama soyutlaması — ileride MinIO/S3'e geçiş için tek nokta.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Kimlik doğrulama akışı
# ---------------------------------------------------------------------------
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# OTP (şifre sıfırlama kodu) ayarları
OTP_CODE_TTL_MINUTES = env.int("OTP_CODE_TTL_MINUTES", default=10)
OTP_DEFAULT_CHANNEL = env("OTP_DEFAULT_CHANNEL", default="email")  # email | whatsapp


# ---------------------------------------------------------------------------
# Klinik / işletme varsayılanları (ClinicSettings boşsa fallback)
# ---------------------------------------------------------------------------
CLINIC_DEFAULTS = {
    "name": "Riva Veteriner Kliniği",
    "phone": "+90 505 956 36 67",
    "address": "Çıldır Mah. 153. Sk. No:20/A, 48700 Marmaris/Muğla",
    "weekday_hours": "09:00 - 19:00",
    "sunday_hours": "13:00 - 19:00",
    "sender_numbers": ["905059563667"],
}


# ---------------------------------------------------------------------------
# E-posta (OTP ve bildirimler) — dev'de konsol, prod'da SMTP
# ---------------------------------------------------------------------------
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Riva Veteriner <no-reply@riva.local>")

MESSAGES_TAGS_OVERRIDE = True
