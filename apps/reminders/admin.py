from django.contrib import admin

from .models import MessageTemplate, OutboundMessage, ReminderRule


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "type", "locale", "channel", "active")
    list_filter = ("type", "locale", "channel", "active")
    search_fields = ("name", "key", "body")


@admin.register(ReminderRule)
class ReminderRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "offset_days", "template", "active")
    list_filter = ("type", "active")


@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = ("owner", "kind", "status", "to_phone", "scheduled_for", "sent_at")
    list_filter = ("status", "kind", "channel")
    search_fields = ("owner__first_name", "owner__last_name", "to_phone", "body")
