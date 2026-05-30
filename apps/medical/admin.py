from django.contrib import admin

from .models import (
    Examination,
    ExaminationTemplate,
    LabResult,
    Note,
    Operation,
    Prescription,
    PrescriptionItem,
)


@admin.register(ExaminationTemplate)
class ExaminationTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    list_filter = ("active",)
    search_fields = ("name", "complaint", "diagnosis")


@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "patient", "vet", "diagnosis", "follow_up_date")
    list_filter = ("vet", "created_at", "follow_up_date")
    search_fields = ("patient__name", "patient__owner__first_name", "patient__owner__last_name", "diagnosis")
    autocomplete_fields = ("patient", "appointment", "vet", "template")
    date_hierarchy = "created_at"


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "patient", "vet", "examination")
    search_fields = ("patient__name", "notes")
    autocomplete_fields = ("patient", "examination", "vet")
    inlines = [PrescriptionItemInline]


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ("date", "patient", "type", "vet", "follow_up_date")
    list_filter = ("vet", "date")
    search_fields = ("patient__name", "type", "result")
    autocomplete_fields = ("patient", "vet")


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ("date", "patient", "test_name")
    search_fields = ("patient__name", "test_name", "result_note")
    autocomplete_fields = ("patient", "examination")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("created_at", "patient", "created_by")
    search_fields = ("patient__name", "body")
    autocomplete_fields = ("patient",)
