from django.contrib import admin

from .models import Patient, Species


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    list_filter = ("active",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "owner", "microchip_no", "deceased")
    list_filter = ("species", "sex", "deceased")
    search_fields = ("name", "microchip_no", "owner__first_name", "owner__last_name")
    autocomplete_fields = ("owner",)
