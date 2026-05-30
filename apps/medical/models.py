"""Tıbbi kayıtlar: muayene, reçete, operasyon, laboratuvar ve serbest not."""

from __future__ import annotations

from django.db import models
from django.urls import reverse

from apps.core.models import BaseModel


class ExaminationTemplate(BaseModel):
    """Muayene formu için düzenlenebilir metin şablonu."""

    name = models.CharField("şablon adı", max_length=120, unique=True)
    complaint = models.TextField("şikayet", blank=True)
    anamnesis = models.TextField("anamnez", blank=True)
    findings = models.TextField("bulgular", blank=True)
    diagnosis = models.TextField("tanı", blank=True)
    treatment_plan = models.TextField("tedavi planı", blank=True)
    active = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "Muayene Şablonu"
        verbose_name_plural = "Muayene Şablonları"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Examination(BaseModel):
    """Hayvanın klinik muayene kaydı."""

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="examinations", verbose_name="hayvan"
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="examinations",
        verbose_name="randevu",
    )
    vet = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="examinations",
        verbose_name="hekim",
    )
    template = models.ForeignKey(
        ExaminationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="examinations",
        verbose_name="şablon",
    )
    complaint = models.TextField("şikayet", blank=True)
    anamnesis = models.TextField("anamnez", blank=True)
    findings = models.TextField("bulgular", blank=True)
    diagnosis = models.TextField("tanı", blank=True)
    treatment_plan = models.TextField("tedavi planı", blank=True)
    notes = models.TextField("notlar", blank=True)
    follow_up_date = models.DateField("kontrol tarihi", null=True, blank=True)

    class Meta:
        verbose_name = "Muayene"
        verbose_name_plural = "Muayeneler"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} · {self.created_at:%d.%m.%Y}"

    def get_absolute_url(self) -> str:
        return reverse("medical:examination_detail", args=[self.pk])


class Prescription(BaseModel):
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="prescriptions", verbose_name="hayvan"
    )
    examination = models.ForeignKey(
        Examination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions",
        verbose_name="muayene",
    )
    vet = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions",
        verbose_name="hekim",
    )
    notes = models.TextField("notlar", blank=True)

    class Meta:
        verbose_name = "Reçete"
        verbose_name_plural = "Reçeteler"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Reçete · {self.patient} · {self.created_at:%d.%m.%Y}"

    def get_absolute_url(self) -> str:
        return reverse("medical:prescription_detail", args=[self.pk])


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="items", verbose_name="reçete"
    )
    drug_name = models.CharField("ilaç", max_length=160)
    dose = models.CharField("doz", max_length=120, blank=True)
    frequency = models.CharField("sıklık", max_length=120, blank=True)
    duration = models.CharField("süre", max_length=120, blank=True)
    note = models.CharField("not", max_length=200, blank=True)

    class Meta:
        verbose_name = "Reçete Kalemi"
        verbose_name_plural = "Reçete Kalemleri"

    def __str__(self) -> str:
        return self.drug_name


class Operation(BaseModel):
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="operations", verbose_name="hayvan"
    )
    date = models.DateTimeField("tarih/saat")
    vet = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operations",
        verbose_name="hekim",
    )
    type = models.CharField("operasyon tipi", max_length=160)
    anesthesia_info = models.TextField("anestezi bilgisi", blank=True)
    drugs_used = models.TextField("kullanılan ilaçlar", blank=True)
    result = models.TextField("sonuç", blank=True)
    notes = models.TextField("notlar", blank=True)
    follow_up_date = models.DateField("kontrol tarihi", null=True, blank=True)
    post_op_instructions = models.TextField("operasyon sonrası talimatlar", blank=True)

    class Meta:
        verbose_name = "Operasyon"
        verbose_name_plural = "Operasyonlar"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.type} · {self.patient}"

    def get_absolute_url(self) -> str:
        return reverse("medical:operation_detail", args=[self.pk])


class LabResult(BaseModel):
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="lab_results", verbose_name="hayvan"
    )
    examination = models.ForeignKey(
        Examination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lab_results",
        verbose_name="muayene",
    )
    test_name = models.CharField("test adı", max_length=160)
    date = models.DateField("tarih")
    result_note = models.TextField("sonuç notu", blank=True)
    file = models.FileField("dosya", upload_to="lab-results/", null=True, blank=True)

    class Meta:
        verbose_name = "Laboratuvar Sonucu"
        verbose_name_plural = "Laboratuvar Sonuçları"
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.test_name} · {self.patient}"

    def get_absolute_url(self) -> str:
        return reverse("medical:lab_result_detail", args=[self.pk])


class Note(BaseModel):
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="medical_notes", verbose_name="hayvan"
    )
    body = models.TextField("not")

    class Meta:
        verbose_name = "Tıbbi Not"
        verbose_name_plural = "Tıbbi Notlar"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Not · {self.patient} · {self.created_at:%d.%m.%Y}"

    def get_absolute_url(self) -> str:
        return reverse("medical:note_detail", args=[self.pk])
