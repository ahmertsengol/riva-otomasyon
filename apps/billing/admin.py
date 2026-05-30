from django.contrib import admin

from .models import Charge, ChargeLine, Payment, ServiceItem


class ChargeLineInline(admin.TabularInline):
    model = ChargeLine
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "default_price", "active")
    list_filter = ("kind", "active")
    search_fields = ("name",)


@admin.register(Charge)
class ChargeAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "patient", "total", "status", "date")
    list_filter = ("status", "date")
    search_fields = ("owner__first_name", "owner__last_name")
    inlines = [ChargeLineInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("charge", "amount", "method", "paid_at")
    list_filter = ("method", "paid_at")
