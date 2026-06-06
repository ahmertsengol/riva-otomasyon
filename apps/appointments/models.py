"""Randevu ve online randevu talebi modelleri."""

from __future__ import annotations

from django.db import models
from django.urls import reverse

from apps.core.models import BaseModel


class Appointment(BaseModel):
    class Type(models.TextChoices):
        GENERAL = "general", "Genel muayene"
        VACCINE = "vaccine", "Aşı"
        PARASITE = "parasite", "Parazit"
        MEDICATION = "medication", "İlaç / Tedavi"
        CONTROL = "control", "Kontrol"
        EMERGENCY = "emergency", "Acil"
        SURGERY = "surgery", "Cerrahi"
        CONSULT = "consult", "Danışma"
        OTHER = "other", "Diğer"

    # Protokol kategorisi → randevu tipi (otomatik sonraki doz randevusu için)
    CATEGORY_TO_TYPE = {
        "vaccine": "vaccine",
        "internal_parasite": "parasite",
        "external_parasite": "parasite",
        "medication": "medication",
    }

    class Status(models.TextChoices):
        REQUESTED = "requested", "Talep geldi"
        CONFIRMED = "confirmed", "Onaylandı"
        ARRIVED = "arrived", "Geldi"
        IN_EXAM = "in_exam", "Muayenede"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal"
        NO_SHOW = "no_show", "Gelmedi"

    class Source(models.TextChoices):
        SCHEDULED = "scheduled", "Planlı"
        WALK_IN = "walk_in", "Hızlı kabul"
        ONLINE_REQUEST = "online_request", "Online talep"
        AUTO_FOLLOWUP = "auto_followup", "Otomatik (sonraki doz)"

    owner = models.ForeignKey(
        "owners.Owner", on_delete=models.CASCADE, related_name="appointments", verbose_name="sahip"
    )
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="appointments", verbose_name="hayvan"
    )
    phone_snapshot = models.CharField("telefon", max_length=30, blank=True)
    starts_at = models.DateTimeField("tarih/saat", db_index=True)
    duration_min = models.PositiveSmallIntegerField("süre (dk)", default=30)
    type = models.CharField("tip", max_length=20, choices=Type.choices, default=Type.GENERAL)
    source = models.CharField(
        "kaynak", max_length=20, choices=Source.choices, default=Source.SCHEDULED, db_index=True
    )
    status = models.CharField(
        "durum", max_length=20, choices=Status.choices, default=Status.CONFIRMED, db_index=True
    )
    assigned_vet = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        verbose_name="atanan hekim",
    )
    # Otomatik sonraki-doz randevusunun hangi protokol/doz için olduğunu taşır
    protocol_definition = models.ForeignKey(
        "vaccines.VaccineDefinition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        verbose_name="protokol",
    )
    dose_number = models.PositiveSmallIntegerField("doz no", null=True, blank=True)
    note = models.TextField("not", blank=True)
    reminder_enabled = models.BooleanField(
        "hatırlatma oluştur", default=True,
        help_text="Kapalıysa bu randevu için otomatik hatırlatma üretilmez.",
    )

    class Meta:
        verbose_name = "Randevu"
        verbose_name_plural = "Randevular"
        ordering = ["starts_at"]

    def __str__(self) -> str:
        return f"{self.patient} · {self.starts_at:%d.%m.%Y %H:%M}"

    def save(self, *args, **kwargs):
        if not self.phone_snapshot and self.owner_id:
            self.phone_snapshot = self.owner.phone
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("appointments:detail", args=[self.pk])

    # Takvim renkleri için durum → ton eşlemesi
    STATUS_TONE = {
        "requested": "#64748b",   # slate
        "confirmed": "#0d9488",   # brand teal
        "arrived": "#0284c7",     # sky
        "in_exam": "#7c3aed",     # violet
        "completed": "#059669",   # emerald
        "cancelled": "#dc2626",   # red
        "no_show": "#d97706",     # amber
    }

    @property
    def color(self) -> str:
        return self.STATUS_TONE.get(self.status, "#0d9488")

    @property
    def protocol_label(self) -> str:
        """Aşı/parazit/ilaç randevusu için net etiket: 'Karma Aşı 2. doz'."""
        if self.protocol_definition_id:
            base = self.protocol_definition.name
            if self.dose_number:
                return f"{base} {self.dose_number}. doz"
            return base
        return self.get_type_display()

    @property
    def is_protocol(self) -> bool:
        return self.type in {self.Type.VACCINE, self.Type.PARASITE, self.Type.MEDICATION}


class AppointmentRequest(BaseModel):
    """Web sitesinden veya elle gelen randevu talebi (henüz randevu değil)."""

    NEW = "new"
    CONVERTED = "converted"
    DISMISSED = "dismissed"
    STATUS_CHOICES = [
        (NEW, "Yeni"),
        (CONVERTED, "Randevuya çevrildi"),
        (DISMISSED, "Yok sayıldı"),
    ]

    SOURCE_WEB = "web"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [(SOURCE_WEB, "Web sitesi"), (SOURCE_MANUAL, "Elle")]

    name = models.CharField("ad soyad", max_length=160)
    phone = models.CharField("telefon", max_length=30)
    pet_name = models.CharField("hayvan adı", max_length=80, blank=True)
    pet_species = models.CharField("hayvan türü", max_length=60, blank=True)
    requested_at = models.CharField("talep edilen tarih/saat", max_length=120, blank=True)
    subject = models.CharField("konu", max_length=120, blank=True)
    message = models.TextField("mesaj", blank=True)
    source = models.CharField("kaynak", max_length=10, choices=SOURCE_CHOICES, default=SOURCE_WEB)
    status = models.CharField(
        "durum", max_length=12, choices=STATUS_CHOICES, default=NEW, db_index=True
    )
    linked_appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name="from_request"
    )

    class Meta:
        verbose_name = "Randevu Talebi"
        verbose_name_plural = "Randevu Talepleri"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} · {self.phone}"
