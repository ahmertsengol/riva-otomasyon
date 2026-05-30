"""Lokal geliştirme ayarları — Docker/Redis/Celery gerektirmez."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

# OTP kodları ve bildirimler dev'de konsola yazılır (gerçek e-posta gönderilmez).
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# Geliştirme kolaylığı: tüm yerel adreslere izin ver.
ALLOWED_HOSTS = ["*"]

# django-extensions / debug araçları buraya eklenebilir (opsiyonel).
