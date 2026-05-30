from django.contrib import admin

from .models import AuditLog, ClinicSettings


@admin.register(ClinicSettings)
class ClinicSettingsAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "model_label", "object_repr")
    list_filter = ("action", "model_label")
    search_fields = ("object_repr", "object_id")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False
