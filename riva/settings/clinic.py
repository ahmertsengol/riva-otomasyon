"""
Klinik PC'sinde CİDDİ kullanım ayarları (lokal ağ, HTTPS henüz yok).

prod.py'den farkı: HTTPS zorlamaz (klinik içi HTTP), ama DEBUG kapalıdır ve statikler
WhiteNoise ile servis edilir. VPS + alan adına geçince prod.py kullanılacak.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Klinik içi ağ: localhost + olası LAN IP'leri
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:8000", "http://127.0.0.1:8000"],
)

# Güvenlik başlıkları (HTTPS olmadığı için SSL redirect YOK)
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

# E-posta: SMTP verilmezse konsola (OTP kodu logda görünür)
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
