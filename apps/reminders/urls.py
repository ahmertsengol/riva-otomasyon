from django.urls import path

from . import views

app_name = "reminders"

urlpatterns = [
    path("", views.queue, name="queue"),
    path("uret/", views.run_generate, name="generate"),
    path("yeni/", views.ManualMessageCreateView.as_view(), name="manual_create"),
    path("sablon-render/", views.render_template_view, name="render_template"),
    path("toplu-gonderildi/", views.bulk_mark_sent, name="bulk_mark_sent"),
    path("<int:pk>/gonderildi/", views.mark_sent, name="mark_sent"),
    path("<int:pk>/iptal/", views.cancel, name="cancel"),
    path("<int:pk>/randevu/", views.create_appointment, name="create_appointment"),
    # Şablonlar & kurallar
    path("sablonlar/", views.templates_and_rules, name="templates"),
    path("sablonlar/yeni/", views.MessageTemplateCreateView.as_view(), name="template_create"),
    path("sablonlar/<int:pk>/duzenle/", views.MessageTemplateUpdateView.as_view(), name="template_update"),
    path("kurallar/yeni/", views.ReminderRuleCreateView.as_view(), name="rule_create"),
    path("kurallar/<int:pk>/duzenle/", views.ReminderRuleUpdateView.as_view(), name="rule_update"),
]
