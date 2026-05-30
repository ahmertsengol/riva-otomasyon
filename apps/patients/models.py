"""Hayvan/hasta profili ve esnek tür (Species) modeli."""

from __future__ import annotations

from datetime import date

from django.db import models
from django.urls import reverse

from apps.core.models import BaseModel


class Species(BaseModel):
    """Esnek hayvan türü listesi (kedi, köpek, kuş, at, sürüngen vb.)."""

    name = models.CharField("tür", max_length=60, unique=True)
    active = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "Tür"
        verbose_name_plural = "Türler"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Patient(BaseModel):
    class Sex(models.TextChoices):
        MALE = "male", "Erkek"
        FEMALE = "female", "Dişi"
        UNKNOWN = "unknown", "Bilinmiyor"

    class Neutered(models.TextChoices):
        YES = "yes", "Evet"
        NO = "no", "Hayır"
        UNKNOWN = "unknown", "Bilinmiyor"

    owner = models.ForeignKey(
        "owners.Owner",
        on_delete=models.CASCADE,
        related_name="patients",
        verbose_name="sahip",
    )
    name = models.CharField("hayvan adı", max_length=80)
    species = models.ForeignKey(
        Species, on_delete=models.PROTECT, related_name="patients", verbose_name="tür"
    )

    # Opsiyonel
    breed = models.CharField("ırk", max_length=80, blank=True)
    sex = models.CharField("cinsiyet", max_length=10, choices=Sex.choices, default=Sex.UNKNOWN)
    birth_date = models.DateField("doğum tarihi", null=True, blank=True)
    age_text = models.CharField("yaş (metin)", max_length=40, blank=True, help_text="Doğum tarihi yoksa ör. '3 yaşında'")
    microchip_no = models.CharField("mikroçip no", max_length=40, blank=True, db_index=True)
    neutered = models.CharField(
        "kısırlaştırma", max_length=10, choices=Neutered.choices, default=Neutered.UNKNOWN
    )
    color = models.CharField("renk", max_length=60, blank=True)
    weight = models.DecimalField("kilo (kg)", max_digits=6, decimal_places=2, null=True, blank=True)
    allergies = models.TextField("alerjiler", blank=True)
    chronic_conditions = models.TextField("kronik hastalıklar", blank=True)
    notes = models.TextField("özel notlar", blank=True)
    photo = models.ImageField("fotoğraf", upload_to="patients/", null=True, blank=True)
    deceased = models.BooleanField("vefat etti", default=False)

    class Meta:
        verbose_name = "Hayvan"
        verbose_name_plural = "Hayvanlar"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.species})"

    def get_absolute_url(self) -> str:
        return reverse("patients:detail", args=[self.pk])

    @property
    def age_display(self) -> str:
        if self.birth_date:
            today = date.today()
            years = today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
            if years >= 1:
                return f"{years} yaş"
            months = (today.year - self.birth_date.year) * 12 + today.month - self.birth_date.month
            return f"{max(months, 0)} aylık"
        return self.age_text or "—"
