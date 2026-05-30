from django.contrib import admin

from .models import Appointment, AppointmentRequest


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("starts_at", "patient", "owner", "type", "status", "assigned_vet")
    list_filter = ("status", "type", "assigned_vet", "starts_at")
    search_fields = (
        "patient__name",
        "owner__first_name",
        "owner__last_name",
        "owner__phone",
        "phone_snapshot",
    )
    date_hierarchy = "starts_at"
    autocomplete_fields = ("owner", "patient", "assigned_vet")


@admin.register(AppointmentRequest)
class AppointmentRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "phone", "pet_name", "subject", "status", "source")
    list_filter = ("status", "source", "created_at")
    search_fields = ("name", "phone", "pet_name", "subject", "message")
    autocomplete_fields = ("linked_appointment",)
