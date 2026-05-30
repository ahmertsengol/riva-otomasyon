from django.contrib import admin

from .models import Owner


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "contact_pref", "kvkk_consent", "created_at")
    list_filter = ("contact_pref", "kvkk_consent")
    search_fields = ("first_name", "last_name", "phone", "email")
