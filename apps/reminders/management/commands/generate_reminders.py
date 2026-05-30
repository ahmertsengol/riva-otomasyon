"""
Yaklaşan/geciken randevu ve aşılar için bekleyen hatırlatma mesajları üretir.

    python manage.py generate_reminders

MVP'de senkron çalışır; prod'da Celery beat ile zamanlanacak (bkz. docs/DEPLOYMENT.md).
Tekrar çalıştırılabilir — mükerrer mesaj üretmez (dedupe).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.reminders.services import generate_reminders


class Command(BaseCommand):
    help = "Hatırlatma kuyruğuna bekleyen mesajlar üretir."

    def handle(self, *args, **options):
        result = generate_reminders()
        self.stdout.write(
            self.style.SUCCESS(
                f"Üretilen mesaj: {result['total']} "
                f"(randevu: {result['appointment']}, aşı: {result['vaccine']})"
            )
        )
