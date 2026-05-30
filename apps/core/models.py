"""Çapraz kesen çekirdek modeller: base mixinler, AuditLog, ClinicSettings."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from .audit import get_actor, get_ip


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("oluşturulma", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("güncellenme", auto_now=True)

    class Meta:
        abstract = True


class AuthoredModel(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="oluşturan",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="güncelleyen",
    )

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel, AuthoredModel):
    """
    Tüm iş modellerinin tabanı.

    save()/delete() sırasında aktif kullanıcıyı created_by/updated_by'a yazar ve
    AuditLog kaydı üretir. `audit = False` sınıf değişkeni ile log kapatılabilir.
    """

    audit = True

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        actor = get_actor()
        is_create = self._state.adding
        if actor is not None:
            if is_create and self.created_by_id is None:
                self.created_by = actor
            self.updated_by = actor
        super().save(*args, **kwargs)
        if self.audit:
            AuditLog.record("create" if is_create else "update", self, actor)

    def delete(self, *args, **kwargs):
        actor = get_actor()
        if self.audit:
            AuditLog.record("delete", self, actor)
        return super().delete(*args, **kwargs)


class AuditLog(models.Model):
    """Kim, hangi kayıtta, ne zaman, hangi işlemi yaptı."""

    CREATE, UPDATE, DELETE = "create", "update", "delete"
    ACTION_CHOICES = [
        (CREATE, "Oluşturma"),
        (UPDATE, "Güncelleme"),
        (DELETE, "Silme"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_label = models.CharField(max_length=120)
    object_id = models.CharField(max_length=64)
    object_repr = models.CharField(max_length=255)
    changes = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Denetim Kaydı"
        verbose_name_plural = "Denetim Kayıtları"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_action_display()} · {self.model_label} #{self.object_id}"

    @classmethod
    def record(cls, action: str, instance, actor=None) -> None:
        cls.objects.create(
            actor=actor,
            action=action,
            model_label=instance._meta.label,
            object_id=str(instance.pk or ""),
            object_repr=str(instance)[:255],
            ip=get_ip(),
        )


class ClinicSettings(models.Model):
    """Tek satırlık (singleton) klinik ayarları."""

    name = models.CharField("klinik adı", max_length=200, default="Riva Veteriner Kliniği")
    logo = models.ImageField("logo", upload_to="clinic/", blank=True, null=True)
    phone = models.CharField("telefon", max_length=40, blank=True)
    email = models.EmailField("e-posta", blank=True)
    address = models.TextField("adres", blank=True)
    weekday_hours = models.CharField("hafta içi saatleri", max_length=40, blank=True)
    sunday_hours = models.CharField("pazar saatleri", max_length=40, blank=True)
    # Hatırlatmalarda arayüzde seçilebilecek gönderen WhatsApp numaraları
    sender_numbers = models.JSONField("gönderen numaralar", default=list, blank=True)
    # E-fatura/vergi alanları (Faz 3 — şimdilik placeholder)
    tax_office = models.CharField("vergi dairesi", max_length=120, blank=True)
    tax_number = models.CharField("vergi/TC no", max_length=40, blank=True)

    class Meta:
        verbose_name = "Klinik Ayarları"
        verbose_name_plural = "Klinik Ayarları"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> ClinicSettings:
        from django.conf import settings as dj_settings

        defaults = dj_settings.CLINIC_DEFAULTS
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "name": defaults["name"],
                "phone": defaults["phone"],
                "address": defaults["address"],
                "weekday_hours": defaults["weekday_hours"],
                "sunday_hours": defaults["sunday_hours"],
                "sender_numbers": list(defaults["sender_numbers"]),
            },
        )
        return obj
