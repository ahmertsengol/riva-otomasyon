"""Aşı protokolü ve uygulama kayıtları."""

from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import BaseModel


class VaccineDefinition(BaseModel):
    """Klinik tarafından düzenlenebilir aşı protokol tanımı."""

    name = models.CharField("aşı adı", max_length=160)
    species = models.ForeignKey(
        "patients.Species", on_delete=models.PROTECT, related_name="vaccine_definitions", verbose_name="tür"
    )
    first_dose_age_text = models.CharField("ilk doz yaşı", max_length=120, blank=True)
    repeat_interval_days = models.PositiveIntegerField("tekrar aralığı (gün)", null=True, blank=True)
    reminder_offset_days = models.PositiveIntegerField("hatırlatma öncesi (gün)", default=7)
    description = models.TextField("açıklama", blank=True)
    active = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "Aşı Protokolü"
        verbose_name_plural = "Aşı Protokolleri"
        ordering = ["species__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "species"], name="unique_vaccine_definition_species")
        ]

    def __str__(self) -> str:
        return f"{self.name} · {self.species.name}"

    def get_absolute_url(self) -> str:
        return reverse("vaccines:protocols")


class VaccineRecord(BaseModel):
    """Hayvana uygulanan aşı ve sonraki doz bilgisi."""

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="vaccine_records", verbose_name="hayvan"
    )
    vaccine_definition = models.ForeignKey(
        VaccineDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
        verbose_name="protokol",
    )
    vaccine_name = models.CharField("aşı adı", max_length=160, blank=True)
    applied_at = models.DateField("uygulama tarihi", default=timezone.localdate)
    next_due_at = models.DateField("sonraki tarih", null=True, blank=True, db_index=True)
    vet = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vaccine_records",
        verbose_name="hekim",
    )
    serial_lot = models.CharField("seri/lot", max_length=80, blank=True)
    expiry_date = models.DateField("son kullanma tarihi", null=True, blank=True)
    note = models.TextField("not", blank=True)

    class Meta:
        verbose_name = "Aşı Kaydı"
        verbose_name_plural = "Aşı Kayıtları"
        ordering = ["-applied_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.display_name} · {self.patient}"

    @property
    def display_name(self) -> str:
        if self.vaccine_definition_id:
            return self.vaccine_definition.name
        return self.vaccine_name or "Aşı"

    @property
    def is_overdue(self) -> bool:
        return bool(self.next_due_at and self.next_due_at < timezone.localdate())

    @property
    def is_upcoming(self) -> bool:
        today = timezone.localdate()
        return bool(self.next_due_at and today <= self.next_due_at <= today + timedelta(days=30))

    def save(self, *args, **kwargs):
        if self.vaccine_definition_id:
            self.vaccine_name = self.vaccine_definition.name
            if self.next_due_at is None and self.vaccine_definition.repeat_interval_days:
                self.next_due_at = self.applied_at + timedelta(
                    days=self.vaccine_definition.repeat_interval_days
                )
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("vaccines:record_detail", args=[self.pk])
