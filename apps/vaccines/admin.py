from django.contrib import admin

from .models import VaccineDefinition, VaccineRecord


@admin.register(VaccineDefinition)
class VaccineDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "repeat_interval_days", "reminder_offset_days", "active")
    list_filter = ("species", "active")
    search_fields = ("name", "description")


@admin.register(VaccineRecord)
class VaccineRecordAdmin(admin.ModelAdmin):
    list_display = ("applied_at", "patient", "display_name", "next_due_at", "vet")
    list_filter = ("applied_at", "next_due_at", "vaccine_definition", "vet")
    search_fields = ("patient__name", "patient__owner__first_name", "patient__owner__last_name", "vaccine_name", "serial_lot")
    autocomplete_fields = ("patient", "vaccine_definition", "vet")
