from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import OTPCode, User


@admin.register(User)
class RivaUserAdmin(UserAdmin):
    list_display = ("username", "display_name", "role", "email", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Klinik", {"fields": ("role", "phone")}),)


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "channel", "purpose", "created_at", "expires_at", "used_at")
    list_filter = ("channel", "purpose")
    readonly_fields = ("code_hash", "created_at")
