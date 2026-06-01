"""
Hafif periyodik zamanlayıcı (Celery/Redis gerektirmez).

Belirli aralıklarla `generate_reminders` çalıştırır; böylece yaklaşan randevu/aşı
hatırlatmaları "Bildirimler"e otomatik düşer. Docker'da ayrı bir servis olarak çalışır.
Prod'da Celery beat'e taşınabilir; çağrılan servis (generate_reminders) aynı kalır.

    python manage.py run_scheduler [--interval 3600]
"""

from __future__ import annotations

import os
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Periyodik hatırlatma üreticisi (hafif zamanlayıcı)."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=None, help="Saniye (varsayılan 3600).")
        parser.add_argument("--once", action="store_true", help="Tek sefer çalış ve çık.")

    def handle(self, *args, **options):
        from apps.reminders.services import generate_reminders

        interval = options["interval"] or int(os.environ.get("REMINDER_INTERVAL_SECONDS", "3600"))

        def tick():
            result = generate_reminders()
            if result["total"]:
                self.stdout.write(self.style.SUCCESS(f"{result['total']} hatırlatma üretildi."))
            return result

        if options["once"]:
            tick()
            return

        self.stdout.write(f"Zamanlayıcı başladı (her {interval} sn'de bir).")
        while True:
            try:
                tick()
                time.sleep(interval)
            except KeyboardInterrupt:
                break
            except Exception as exc:  # DB henüz hazır değilse vb. — kısa bekleyip yeniden dene
                self.stderr.write(f"Zamanlayıcı hatası, 15 sn sonra tekrar: {exc}")
                time.sleep(15)
