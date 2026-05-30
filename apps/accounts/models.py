"""Kullanıcı (personel) ve OTP (şifre sıfırlama kodu) modelleri."""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Klinik personeli. MVP'de tek kullanıcı (admin) kullanılır; `role` alanı ve
    ekip alanları ileride çoklu-kullanıcı/yetki için hazırdır.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Yönetici"
        VET = "vet", "Veteriner Hekim"
        ASSISTANT = "assistant", "Asistan / Sekreter"
        CASHIER = "cashier", "Kasa"

    role = models.CharField(
        "rol", max_length=20, choices=Role.choices, default=Role.ADMIN
    )
    phone = models.CharField("telefon", max_length=30, blank=True)

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.username

    @property
    def is_vet(self) -> bool:
        return self.role in {self.Role.VET, self.Role.ADMIN}


class OTPCode(models.Model):
    """
    Şifre sıfırlama / güvenlik doğrulama kodu.

    Kod düz metin saklanmaz; hash'lenir. Kanal soyutlaması (e-posta / WhatsApp)
    `apps.core.otp` içinde yönetilir.
    """

    PURPOSE_PASSWORD_RESET = "password_reset"
    PURPOSE_CHOICES = [(PURPOSE_PASSWORD_RESET, "Şifre sıfırlama")]

    CHANNEL_EMAIL = "email"
    CHANNEL_WHATSAPP = "whatsapp"
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "E-posta"),
        (CHANNEL_WHATSAPP, "WhatsApp"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otp_codes"
    )
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(
        max_length=30, choices=PURPOSE_CHOICES, default=PURPOSE_PASSWORD_RESET
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_EMAIL)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OTP Kodu"
        verbose_name_plural = "OTP Kodları"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} · {self.get_channel_display()} · {self.created_at:%d.%m.%Y %H:%M}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and not self.is_expired and self.attempts < 5

    @classmethod
    def issue(cls, user, *, channel: str, purpose: str = PURPOSE_PASSWORD_RESET) -> tuple[OTPCode, str]:
        """Yeni 6 haneli kod üretir; (kayıt, düz_kod) döner. Düz kod yalnızca gönderim içindir."""
        code = f"{secrets.randbelow(1_000_000):06d}"
        ttl = getattr(settings, "OTP_CODE_TTL_MINUTES", 10)
        # Aynı kullanıcının önceki kullanılmamış kodlarını geçersiz kıl.
        cls.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(
            used_at=timezone.now()
        )
        otp = cls.objects.create(
            user=user,
            code_hash=make_password(code),
            purpose=purpose,
            channel=channel,
            expires_at=timezone.now() + timedelta(minutes=ttl),
        )
        return otp, code

    def verify(self, code: str) -> bool:
        if not self.is_usable:
            return False
        self.attempts += 1
        ok = check_password(code, self.code_hash)
        if ok:
            self.used_at = timezone.now()
        self.save(update_fields=["attempts", "used_at"])
        return ok
