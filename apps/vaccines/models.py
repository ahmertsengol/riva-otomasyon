"""Aşı protokolü ve uygulama kayıtları."""

from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import BaseModel


class VaccineDefinition(BaseModel):
    """
    Klinik tarafından düzenlenebilir koruyucu/tedavi protokol tanımı.

    Tek motor; `category` ile aşı / iç parazit / dış parazit / ilaç kürü ayrılır.
    Hepsi aynı davranır: birincil seri (series_doses/interval) + sonrası rapel
    (repeat_interval_days). Yalnızca hatırlatma metni ve UI etiketi kategoriye göre değişir.
    """

    class Category(models.TextChoices):
        VACCINE = "vaccine", "Aşı"
        INTERNAL_PARASITE = "internal_parasite", "İç Parazit"
        EXTERNAL_PARASITE = "external_parasite", "Dış Parazit"
        MEDICATION = "medication", "İlaç / Tedavi"

    category = models.CharField(
        "kategori", max_length=20, choices=Category.choices,
        default=Category.VACCINE, db_index=True,
    )
    name = models.CharField("ad", max_length=160)
    species = models.ForeignKey(
        "patients.Species", on_delete=models.PROTECT, related_name="vaccine_definitions", verbose_name="tür"
    )
    first_dose_age_text = models.CharField("ilk doz yaşı", max_length=120, blank=True)
    repeat_interval_days = models.PositiveIntegerField(
        "tekrar aralığı (gün)", null=True, blank=True,
        help_text="Birincil seri tamamlandıktan sonraki rapel aralığı (ör. yıllık = 365).",
    )
    series_doses = models.PositiveSmallIntegerField(
        "birincil seri doz sayısı", default=1,
        help_text="Örn. yavru karma için 2-3. 1 ise tek doz + rapel.",
    )
    series_interval_days = models.PositiveIntegerField(
        "seri doz aralığı (gün)", null=True, blank=True,
        help_text="Birincil serideki dozlar arası gün (ör. 21). Boşsa tekrar aralığı kullanılır.",
    )
    reminder_offset_days = models.PositiveIntegerField("hatırlatma öncesi (gün)", default=7)
    description = models.TextField("açıklama", blank=True)
    active = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "Protokol"
        verbose_name_plural = "Protokoller"
        ordering = ["category", "species__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "species", "category"],
                name="unique_vaccine_definition_species",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} · {self.species.name}"

    @property
    def is_vaccine(self) -> bool:
        return self.category == self.Category.VACCINE

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
    def category(self) -> str | None:
        return self.vaccine_definition.category if self.vaccine_definition_id else None

    @property
    def dose_number(self) -> int:
        """Bu kayıt, bu protokolün kaçıncı dozu (1 tabanlı)."""
        if not self.vaccine_definition_id:
            return 1
        prior = VaccineRecord.objects.filter(
            patient_id=self.patient_id,
            vaccine_definition_id=self.vaccine_definition_id,
            applied_at__lte=self.applied_at,
        )
        if self.pk:
            prior = prior.exclude(pk=self.pk)
        return prior.count() + 1

    @property
    def next_dose_number(self) -> int:
        """next_due_at hangi doza işaret ediyor (rapel ise yine bir sonraki)."""
        return self.dose_number + 1

    @property
    def is_overdue(self) -> bool:
        return bool(self.next_due_at and self.next_due_at < timezone.localdate())

    @property
    def is_upcoming(self) -> bool:
        today = timezone.localdate()
        return bool(self.next_due_at and today <= self.next_due_at <= today + timedelta(days=30))

    def save(self, *args, **kwargs):
        if self.vaccine_definition_id:
            definition = self.vaccine_definition
            self.vaccine_name = definition.name
            if self.next_due_at is None:
                self.next_due_at = self._compute_next_due(definition)
        super().save(*args, **kwargs)
        # Yeni doz, aynı (hayvan, protokol) için ÖNCEKİ kayıtların "sonraki tarih"ini
        # geçersiz kılar → yalnızca en güncel kayıt due/overdue'da görünür (liste şişmesin).
        if self.vaccine_definition_id:
            VaccineRecord.objects.filter(
                patient_id=self.patient_id,
                vaccine_definition_id=self.vaccine_definition_id,
                applied_at__lte=self.applied_at,
                next_due_at__isnull=False,
            ).exclude(pk=self.pk).update(next_due_at=None)

    def _compute_next_due(self, definition):
        """Birincil seri devam ediyorsa seri aralığı, bittiyse rapel aralığı."""
        prior = VaccineRecord.objects.filter(
            patient_id=self.patient_id, vaccine_definition_id=definition.pk
        )
        if self.pk:
            prior = prior.exclude(pk=self.pk)
        dose_number = prior.filter(applied_at__lte=self.applied_at).count() + 1
        in_primary_series = dose_number < (definition.series_doses or 1)
        if in_primary_series and definition.series_interval_days:
            return self.applied_at + timedelta(days=definition.series_interval_days)
        if definition.repeat_interval_days:
            return self.applied_at + timedelta(days=definition.repeat_interval_days)
        return None

    def get_absolute_url(self) -> str:
        return reverse("vaccines:record_detail", args=[self.pk])
