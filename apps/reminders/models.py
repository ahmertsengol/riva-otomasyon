"""
Hatırlatma sistemi: mesaj şablonları, kurallar ve gönderim kuyruğu/log.

MVP'de gerçek otomatik gönderim YOK. `generate_reminders` komutu yaklaşan/geciken
randevu ve aşıları tarayıp `OutboundMessage(pending)` üretir; personel `wa.me` linkiyle
elle gönderir ve "Gönderildi" işaretler. Gerçek sağlayıcı (Cloud API) ileride
`apps.reminders.providers` üzerinden eklenir; üst katman değişmez.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


def render_body(template_body: str, context: dict) -> str:
    """Basit {{anahtar}} yer tutucu değişimi."""
    out = template_body
    for key, value in context.items():
        out = out.replace("{{" + key + "}}", str(value if value is not None else ""))
    return out


class MessageTemplate(BaseModel):
    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"

    class Locale(models.TextChoices):
        TR = "tr", "Türkçe"
        EN = "en", "İngilizce"

    class Type(models.TextChoices):
        APPOINTMENT = "appointment", "Randevu"
        VACCINE = "vaccine", "Aşı"
        GENERAL = "general", "Genel"

    key = models.SlugField("anahtar", max_length=60, unique=True)
    name = models.CharField("ad", max_length=120)
    channel = models.CharField("kanal", max_length=20, choices=Channel.choices, default=Channel.WHATSAPP)
    locale = models.CharField("dil", max_length=5, choices=Locale.choices, default=Locale.TR)
    type = models.CharField("tip", max_length=20, choices=Type.choices, default=Type.APPOINTMENT)
    body = models.TextField(
        "metin",
        help_text="Yer tutucular: {{owner_name}}, {{pet_name}}, {{date}}, {{time}}, {{vaccine}}, {{clinic}}",
    )
    active = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "Mesaj Şablonu"
        verbose_name_plural = "Mesaj Şablonları"
        ordering = ["type", "locale", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_locale_display()})"


class ReminderRule(BaseModel):
    """
    Ne zaman hatırlatma üretileceğini tanımlar.

    offset_days: hedef tarihten (randevu tarihi / aşı sonraki tarihi) KAÇ GÜN ÖNCE.
    0 = aynı gün. Negatif = tarihten sonra (geciken aşı tekrar hatırlatması için).
    """

    type = models.CharField(
        "tip", max_length=20, choices=MessageTemplate.Type.choices, default=MessageTemplate.Type.APPOINTMENT
    )
    name = models.CharField("ad", max_length=120)
    offset_days = models.IntegerField("gün farkı (önce +/sonra -)", default=1)
    template = models.ForeignKey(
        MessageTemplate, on_delete=models.PROTECT, related_name="rules", verbose_name="şablon"
    )
    active = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "Hatırlatma Kuralı"
        verbose_name_plural = "Hatırlatma Kuralları"
        ordering = ["type", "-offset_days"]

    def __str__(self) -> str:
        return f"{self.name} ({self.offset_days:+d} gün)"


class OutboundMessage(BaseModel):
    """Gönderim kuyruğu + log kaydı."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (PENDING, "Bekliyor"),
        (SENT, "Gönderildi"),
        (FAILED, "Başarısız"),
        (CANCELLED, "İptal edildi"),
    ]

    KIND_APPOINTMENT = "appointment"
    KIND_VACCINE = "vaccine"
    KIND_MANUAL = "manual"
    KIND_CHOICES = [
        (KIND_APPOINTMENT, "Randevu"),
        (KIND_VACCINE, "Aşı"),
        (KIND_MANUAL, "Elle"),
    ]

    owner = models.ForeignKey(
        "owners.Owner", on_delete=models.CASCADE, related_name="messages", verbose_name="sahip"
    )
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.SET_NULL, null=True, blank=True, related_name="messages"
    )
    kind = models.CharField("tür", max_length=20, choices=KIND_CHOICES, default=KIND_MANUAL)
    channel = models.CharField(
        "kanal", max_length=20, choices=MessageTemplate.Channel.choices, default=MessageTemplate.Channel.WHATSAPP
    )
    sender_number = models.CharField("gönderen numara", max_length=30, blank=True)
    to_phone = models.CharField("alıcı telefon", max_length=30)
    body = models.TextField("mesaj")
    status = models.CharField("durum", max_length=12, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    scheduled_for = models.DateField("planlanan tarih", null=True, blank=True)
    sent_at = models.DateTimeField("gönderim zamanı", null=True, blank=True)
    error = models.CharField("hata", max_length=255, blank=True)
    wa_link = models.URLField("wa.me linki", max_length=600, blank=True)

    # İlgili kayıtlar (opsiyonel) + tekrar üretimi engellemek için tekil anahtar
    appointment = models.ForeignKey(
        "appointments.Appointment", on_delete=models.SET_NULL, null=True, blank=True, related_name="messages"
    )
    vaccine_record = models.ForeignKey(
        "vaccines.VaccineRecord", on_delete=models.SET_NULL, null=True, blank=True, related_name="messages"
    )
    dedupe_key = models.CharField(max_length=180, blank=True, default="", db_index=True)

    class Meta:
        verbose_name = "Giden Mesaj"
        verbose_name_plural = "Giden Mesajlar"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["dedupe_key"],
                condition=~models.Q(dedupe_key=""),
                name="unique_outbound_dedupe_key",
            )
        ]

    def __str__(self) -> str:
        return f"{self.owner} · {self.get_status_display()}"
