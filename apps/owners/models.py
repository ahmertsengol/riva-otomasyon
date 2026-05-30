"""Sahip (pet sahibi) modeli — KVKK ve iletişim tercihi dahil."""

from __future__ import annotations

from django.db import models
from django.urls import reverse

from apps.core.models import BaseModel


class Owner(BaseModel):
    class ContactPref(models.TextChoices):
        PHONE = "phone", "Telefon"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "E-posta"
        NONE = "none", "İletişim istemiyor"

    # Zorunlu
    first_name = models.CharField("ad", max_length=80)
    last_name = models.CharField("soyad", max_length=80)
    phone = models.CharField("telefon", max_length=30, db_index=True)

    # Opsiyonel
    tc_no = models.CharField("T.C. kimlik no", max_length=11, blank=True)
    email = models.EmailField("e-posta", blank=True)
    address = models.TextField("adres", blank=True)
    il = models.CharField("il", max_length=50, blank=True)
    ilce = models.CharField("ilçe", max_length=50, blank=True)
    notes = models.TextField("notlar", blank=True)
    contact_pref = models.CharField(
        "iletişim tercihi",
        max_length=20,
        choices=ContactPref.choices,
        default=ContactPref.WHATSAPP,
    )

    # KVKK / izinler
    kvkk_consent = models.BooleanField("KVKK onayı", default=False)
    kvkk_consent_at = models.DateTimeField("KVKK onay tarihi", null=True, blank=True)
    marketing_consent = models.BooleanField("ticari ileti izni", default=False)

    class Meta:
        verbose_name = "Sahip"
        verbose_name_plural = "Sahipler"
        ordering = ["first_name", "last_name"]
        indexes = [models.Index(fields=["last_name", "first_name"])]

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_absolute_url(self) -> str:
        return reverse("owners:detail", args=[self.pk])

    @property
    def wa_phone(self) -> str:
        """WhatsApp linki için sadece rakamlar (90... formatına yaklaştırır)."""
        digits = "".join(ch for ch in self.phone if ch.isdigit())
        if digits.startswith("0"):
            digits = "90" + digits[1:]
        elif not digits.startswith("90") and len(digits) == 10:
            digits = "90" + digits
        return digits

    @property
    def balance(self) -> float:
        """Toplam borç (Σ işlem − Σ tahsilat). Billing yoksa 0 döner."""
        try:
            from django.db.models import Sum

            from apps.billing.models import Charge, Payment

            charged = Charge.objects.filter(owner=self).aggregate(t=Sum("total"))["t"] or 0
            paid = (
                Payment.objects.filter(charge__owner=self).aggregate(t=Sum("amount"))["t"]
                or 0
            )
            return float(charged) - float(paid)
        except Exception:
            return 0.0
