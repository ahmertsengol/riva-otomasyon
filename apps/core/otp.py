"""
OTP gönderim kanalı soyutlaması.

MVP'de e-posta kanalı aktiftir. WhatsApp kanalı aynı arayüzü uygular ama şimdilik
stub'dur (gerçek gönderim yapmaz) — ileride `apps.reminders` sağlayıcısıyla bağlanacak.
Kanal değiştirmek için üst katman (views) değişmez; sadece `get_channel()` farklı döner.
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail


class BaseOTPChannel:
    key: str = ""

    def can_use(self, user) -> bool:
        raise NotImplementedError

    def send(self, user, code: str) -> None:
        raise NotImplementedError

    def target_hint(self, user) -> str:
        """Kullanıcıya gösterilecek maskelenmiş hedef (ör. a***@gmail.com)."""
        return ""


class EmailOTPChannel(BaseOTPChannel):
    key = "email"

    def can_use(self, user) -> bool:
        return bool(user.email)

    def send(self, user, code: str) -> None:
        send_mail(
            subject="Riva Veteriner — Doğrulama Kodu",
            message=(
                f"Merhaba {user.display_name},\n\n"
                f"Şifre sıfırlama doğrulama kodunuz: {code}\n"
                f"Kod {getattr(settings, 'OTP_CODE_TTL_MINUTES', 10)} dakika geçerlidir.\n\n"
                "Bu işlemi siz başlatmadıysanız bu e-postayı yok sayın."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    def target_hint(self, user) -> str:
        return _mask_email(user.email)


class WhatsAppOTPChannel(BaseOTPChannel):
    """Stub — MVP'de gerçek gönderim yok. Kod konsola/loga yazılır."""

    key = "whatsapp"

    def can_use(self, user) -> bool:
        return bool(user.phone)

    def send(self, user, code: str) -> None:
        # İleride apps.reminders Cloud API sağlayıcısına bağlanacak.
        print(f"[OTP/WhatsApp-STUB] {user.phone} -> kod: {code}")

    def target_hint(self, user) -> str:
        return _mask_phone(user.phone)


_CHANNELS = {c.key: c for c in (EmailOTPChannel(), WhatsAppOTPChannel())}


def get_channel(key: str | None = None) -> BaseOTPChannel:
    key = key or getattr(settings, "OTP_DEFAULT_CHANNEL", "email")
    return _CHANNELS.get(key, _CHANNELS["email"])


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    name, domain = email.split("@", 1)
    shown = name[0] if name else ""
    return f"{shown}{'*' * max(len(name) - 1, 1)}@{domain}"


def _mask_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 4:
        return "***"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"
