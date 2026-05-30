"""
Basit kasa çekirdeği: hizmet/ürün, işlem (Charge) + satırlar, tahsilat (Payment).

E-fatura/POS entegrasyonuna hazır tasarlandı (vergi alanları ClinicSettings'te placeholder,
ödeme yöntemi/referansı modelde). MVP'de e-fatura yalnızca SİMÜLASYON ekranıdır.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from apps.core.models import BaseModel

TWO = Decimal("0.01")


class ServiceItem(BaseModel):
    class Kind(models.TextChoices):
        SERVICE = "service", "Hizmet"
        PRODUCT = "product", "Ürün"

    name = models.CharField("ad", max_length=160)
    kind = models.CharField("tür", max_length=10, choices=Kind.choices, default=Kind.SERVICE)
    default_price = models.DecimalField("varsayılan fiyat", max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "Hizmet / Ürün"
        verbose_name_plural = "Hizmetler / Ürünler"
        ordering = ["kind", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kind_display()})"


class Charge(BaseModel):
    """Bir muayene/işlem için ücret başlığı (satırlardan oluşur)."""

    PAID = "paid"
    PARTIAL = "partial"
    PENDING = "pending"
    STATUS_CHOICES = [
        (PAID, "Ödendi"),
        (PARTIAL, "Kısmi ödendi"),
        (PENDING, "Bekliyor"),
    ]

    owner = models.ForeignKey(
        "owners.Owner", on_delete=models.CASCADE, related_name="charges", verbose_name="sahip"
    )
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="charges", verbose_name="hayvan",
    )
    examination = models.ForeignKey(
        "medical.Examination", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="charges", verbose_name="muayene",
    )
    date = models.DateField("tarih", auto_now_add=True)
    total = models.DecimalField("toplam", max_digits=10, decimal_places=2, default=0)
    status = models.CharField("durum", max_length=10, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    note = models.CharField("açıklama", max_length=255, blank=True)

    class Meta:
        verbose_name = "İşlem / Ücret"
        verbose_name_plural = "İşlemler / Ücretler"
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return f"İşlem #{self.pk} · {self.owner}"

    def get_absolute_url(self) -> str:
        return reverse("billing:charge_detail", args=[self.pk])

    @property
    def paid_amount(self) -> Decimal:
        return self.payments.aggregate(t=Sum("amount"))["t"] or Decimal("0")

    @property
    def balance(self) -> Decimal:
        return (self.total or Decimal("0")) - self.paid_amount

    def recompute(self, save: bool = True) -> None:
        total = self.lines.aggregate(t=Sum("line_total"))["t"] or Decimal("0")
        self.total = total.quantize(TWO)
        paid = self.paid_amount
        if paid <= 0:
            self.status = self.PENDING
        elif paid >= self.total:
            self.status = self.PAID
        else:
            self.status = self.PARTIAL
        if save:
            super().save(update_fields=["total", "status", "updated_at", "updated_by"])


class ChargeLine(BaseModel):
    charge = models.ForeignKey(Charge, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(
        ServiceItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="lines"
    )
    description = models.CharField("açıklama", max_length=200)
    qty = models.DecimalField("adet", max_digits=8, decimal_places=2, default=1)
    unit_price = models.DecimalField("birim fiyat", max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField("satır tutarı", max_digits=10, decimal_places=2, default=0)

    audit = False  # satır denetimi gürültü yaratmasın; başlık (Charge) denetlenir

    class Meta:
        verbose_name = "İşlem Satırı"
        verbose_name_plural = "İşlem Satırları"

    def __str__(self) -> str:
        return f"{self.description} ×{self.qty}"

    def save(self, *args, **kwargs):
        self.line_total = (Decimal(self.qty) * Decimal(self.unit_price)).quantize(TWO)
        super().save(*args, **kwargs)


class Payment(BaseModel):
    class Method(models.TextChoices):
        CASH = "cash", "Nakit"
        CARD = "card", "Kart"
        TRANSFER = "transfer", "Havale/EFT"
        UNPAID = "unpaid", "Ödenmedi"

    charge = models.ForeignKey(Charge, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField("tutar", max_digits=10, decimal_places=2)
    method = models.CharField("yöntem", max_length=10, choices=Method.choices, default=Method.CASH)
    paid_at = models.DateTimeField("ödeme zamanı", default=timezone.now, db_index=True)
    reference = models.CharField("referans", max_length=120, blank=True)  # POS/link ödeme için (Faz 4)
    note = models.CharField("not", max_length=255, blank=True)

    class Meta:
        verbose_name = "Tahsilat"
        verbose_name_plural = "Tahsilatlar"
        ordering = ["-paid_at"]

    def __str__(self) -> str:
        return f"{self.amount} ₺ · {self.get_method_display()}"
