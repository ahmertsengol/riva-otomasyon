"""
Üretim için güvenli ilk kurulum (idempotent, SAHTE VERİ İÇERMEZ).

Her konteyner açılışında çalıştırılabilir; yalnızca eksik olan yapılandırma/referans
verisini ekler, var olanı silmez/değiştirmez:
  - admin kullanıcısı (şifre: ADMIN_PASSWORD ortam değişkeni veya 'admin123')
  - klinik ayarları + logo
  - türler, aşı protokolleri, mesaj şablonları + hatırlatma kuralları, hizmet/ürün kalemleri

Demo (sahte sahip/hayvan/randevu) için: `python manage.py seed_demo`.
"""

from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings as dj_settings
from django.core.files import File
from django.core.management.base import BaseCommand

SPECIES = [
    "Köpek", "Kedi", "Kuş", "At", "Hamster", "Kaplumbağa",
    "Sürüngen", "Koyun", "Keçi", "Tavşan", "Diğer",
]

# (kategori, tür, ad, ilk doz yaşı, tekrar gün, hatırlatma gün, seri doz, seri aralık, açıklama)
# TEK MOTOR: aşı + iç/dış parazit + ilaç kürü. Aralıklar/dozlar yaygın uygulamaya göre
# DOLDURULMUŞ ÖRNEKLERDİR; bölgeye, ürüne ve güncel mevzuata göre değişir →
# klinik veteriner hekimi DOĞRULAYIP düzenlemelidir (her alan UI'dan düzenlenebilir).
_DISC = " (Düzenlenebilir örnek — veteriner aralığı/dozu doğrulamalı.)"
VACCINE_SPECS = [
    # ---- Köpek aşıları ----
    ("vaccine", "Köpek", "Karma (DHPP)", "6-8 haftalık", 365, 14, 3, 21,
     "Parvo, gençlik hastalığı (distemper), hepatit, parainfluenza. Yavru serisi + yıllık rapel." + _DISC),
    ("vaccine", "Köpek", "Kuduz", "12 haftalık", 365, 14, 1, None,
     "Yasal olarak gerekli olabilir; tek doz + yıllık rapel." + _DISC),
    ("vaccine", "Köpek", "Bronşin (Kennel Cough)", "8 haftalık", 365, 14, 1, None,
     "Bordetella/parainfluenza (kennel cough); genelde yıllık." + _DISC),
    ("vaccine", "Köpek", "Leptospira", "8-9 haftalık", 365, 14, 2, 21,
     "Leptospirosis; 2 dozluk seri + yıllık rapel (çoğu zaman karma içinde)." + _DISC),
    # ---- Kedi aşıları ----
    ("vaccine", "Kedi", "Karma (FVRCP)", "8-9 haftalık", 365, 14, 3, 21,
     "Nezle (herpes/calici) + panlökopeni. Yavru serisi + yıllık rapel." + _DISC),
    ("vaccine", "Kedi", "Kuduz", "12 haftalık", 365, 14, 1, None,
     "Tek doz + yıllık rapel." + _DISC),
    ("vaccine", "Kedi", "Lösemi (FeLV)", "8-9 haftalık", 365, 14, 2, 21,
     "Feline lösemi virüsü; 2 dozluk seri + yıllık rapel." + _DISC),
    # ---- İç parazit (solucan) — yavru sık, erişkin ~3 ayda bir ----
    ("internal_parasite", "Köpek", "İç Parazit (Solucan)", "Yavru aylık, erişkin 3 ayda bir",
     90, 7, 1, None, "Bağırsak solucanları; erişkinde genelde 3 ayda bir." + _DISC),
    ("internal_parasite", "Kedi", "İç Parazit (Solucan)", "Yavru aylık, erişkin 3 ayda bir",
     90, 7, 1, None, "Bağırsak solucanları; erişkinde genelde 3 ayda bir." + _DISC),
    # ---- Kalp kurdu koruması (heartworm) — endemik bölgede aylık ----
    ("internal_parasite", "Köpek", "Kalp Kurdu Koruması", "Aylık (endemik bölgede)",
     30, 5, 1, None, "Heartworm koruması; endemik bölgelerde aylık." + _DISC),
    # ---- Dış parazit (pire-kene) — ürüne göre genelde aylık ----
    ("external_parasite", "Köpek", "Dış Parazit (Pire-Kene)", "Aylık",
     30, 5, 1, None, "Pire-kene; ürüne göre genelde aylık (bazı ürünler 3 aylık)." + _DISC),
    ("external_parasite", "Kedi", "Dış Parazit (Pire-Kene)", "Aylık",
     30, 5, 1, None, "Pire-kene; ürüne göre genelde aylık (bazı ürünler 3 aylık)." + _DISC),
    # ---- İlaç kürleri (örnek; ilaca/duruma göre klinik düzenler) ----
    ("medication", "Köpek", "Antibiyotik Kürü (örnek)", "—", None, 1, 7, 1,
     "Örnek: 7 gün boyunca günde 1 doz. İlaca göre doz/gün sayısını düzenleyin." + _DISC),
    ("medication", "Kedi", "Antibiyotik Kürü (örnek)", "—", None, 1, 7, 1,
     "Örnek: 7 gün boyunca günde 1 doz. İlaca göre doz/gün sayısını düzenleyin." + _DISC),
    ("medication", "Köpek", "Ağrı Kesici / NSAID Kürü (örnek)", "—", None, 1, 3, 1,
     "Örnek: 3 gün boyunca günde 1 doz." + _DISC),
    ("medication", "Kedi", "Ağrı Kesici / NSAID Kürü (örnek)", "—", None, 1, 3, 1,
     "Örnek: 3 gün boyunca günde 1 doz." + _DISC),
]

SERVICE_SPECS = [
    ("Genel Muayene", "service", 350),
    ("Karma Aşı", "service", 450),
    ("Kuduz Aşı", "service", 300),
    ("Mikroçip Uygulama", "service", 500),
    ("Mama (1.5 kg)", "product", 600),
    ("Bit-Pire Damlası", "product", 250),
]


class Command(BaseCommand):
    help = "Üretim için güvenli ilk kurulum (admin + yapılandırma; sahte veri yok)."

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.billing.models import ServiceItem
        from apps.core.models import ClinicSettings
        from apps.patients.models import Species
        from apps.reminders.models import MessageTemplate, ReminderRule
        from apps.vaccines.models import VaccineDefinition

        # Admin
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "first_name": "Klinik", "last_name": "Yöneticisi",
                "email": os.environ.get("ADMIN_EMAIL", "info.rivaveteriner@gmail.com"),
                "role": User.Role.ADMIN, "is_staff": True, "is_superuser": True,
            },
        )
        if created:
            admin.set_password(os.environ.get("ADMIN_PASSWORD", "admin123"))
            admin.save()
            self.stdout.write(self.style.SUCCESS("Yönetici oluşturuldu (admin)."))

        # Klinik ayarları + logo
        clinic = ClinicSettings.load()
        if not clinic.logo:
            logo_path = Path(dj_settings.BASE_DIR) / "static" / "img" / "riva-logo.jpg"
            if logo_path.exists():
                with open(logo_path, "rb") as f:
                    clinic.logo.save("riva-logo.jpg", File(f), save=True)

        # Türler
        species_map = {n: Species.objects.get_or_create(name=n)[0] for n in SPECIES}

        # Protokoller (aşı + iç/dış parazit + ilaç)
        for category, sp_name, name, first, repeat, remind, doses, interval, desc in VACCINE_SPECS:
            VaccineDefinition.objects.get_or_create(
                species=species_map[sp_name], name=name, category=category,
                defaults={
                    "first_dose_age_text": first, "repeat_interval_days": repeat,
                    "reminder_offset_days": remind, "series_doses": doses,
                    "series_interval_days": interval, "description": desc,
                },
            )

        # Hizmet / ürün
        for name, kind, price in SERVICE_SPECS:
            ServiceItem.objects.get_or_create(
                name=name, defaults={"kind": kind, "default_price": price}
            )

        # Mesaj şablonları + kurallar
        T, L = MessageTemplate.Type, MessageTemplate.Locale
        catalog = [
            ("randevu-olusturuldu", "Randevu Oluşturuldu", T.APPOINTMENT, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için {{date}} {{time}} randevunuz oluşturulmuştur. {{clinic}}"),
            ("randevu-hatirlatma", "Randevu Hatırlatma (1 gün önce)", T.APPOINTMENT, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için yarın {{date}} {{time}} randevunuzu hatırlatırız. "
             "Gelemeyecekseniz lütfen bizi arayın. {{clinic}}"),
            ("randevu-gelmedi", "Randevuya Gelinmedi", T.APPOINTMENT, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için {{date}} randevunuza gelemediniz. "
             "Yeni randevu için bizi arayabilirsiniz. {{clinic}}"),
            ("asi-yaklasan", "Aşı Yaklaşıyor", T.VACCINE, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için {{vaccine}} aşısının zamanı yaklaşıyor "
             "(son tarih {{date}}). Randevu için bizi arayabilirsiniz. {{clinic}}"),
            ("asi-geciken", "Aşı Gecikti", T.VACCINE, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için {{vaccine}} aşısı {{date}} tarihinde gecikti. "
             "En kısa sürede randevu almanızı öneririz. {{clinic}}"),
            ("ic-parazit-yaklasan", "İç Parazit Yaklaşıyor", T.VACCINE, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için iç parazit (solucan) uygulamasının zamanı "
             "yaklaşıyor (son tarih {{date}}). Randevu için bizi arayabilirsiniz. {{clinic}}"),
            ("ic-parazit-geciken", "İç Parazit Gecikti", T.VACCINE, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için iç parazit uygulaması {{date}} tarihinde gecikti. "
             "En kısa sürede randevu almanızı öneririz. {{clinic}}"),
            ("dis-parazit-yaklasan", "Dış Parazit Yaklaşıyor", T.VACCINE, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için dış parazit (pire-kene) uygulamasının zamanı "
             "yaklaşıyor (son tarih {{date}}). Randevu için bizi arayabilirsiniz. {{clinic}}"),
            ("dis-parazit-geciken", "Dış Parazit Gecikti", T.VACCINE, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için dış parazit uygulaması {{date}} tarihinde gecikti. "
             "En kısa sürede randevu almanızı öneririz. {{clinic}}"),
            ("ilac-yaklasan", "İlaç Dozu Yaklaşıyor", T.VACCINE, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için {{vaccine}} sonraki dozunun zamanı geldi ({{date}}). "
             "{{clinic}}"),
            ("ilac-geciken", "İlaç Dozu Gecikti", T.VACCINE, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için {{vaccine}} dozu {{date}} tarihinde gecikti. "
             "Lütfen aksatmayın. {{clinic}}"),
            ("kontrol-hatirlatma", "Kontrol Hatırlatma", T.CONTROL, L.TR,
             "Sayın {{owner_name}}, {{pet_name}} için kontrol zamanı geldi ({{date}}). "
             "Randevu için bizi arayabilirsiniz. {{clinic}}"),
            ("tahsilat-hatirlatma", "Ödeme Hatırlatma", T.PAYMENT, L.TR,
             "Sayın {{owner_name}}, {{clinic}} kliniğimizde {{amount}} ₺ ödenmemiş bakiyeniz bulunmaktadır. "
             "Bilginize, teşekkür ederiz."),
            ("tesekkur", "Teşekkür / Geçmiş Olsun", T.GENERAL, L.TR,
             "Sayın {{owner_name}}, {{pet_name}}'i bize emanet ettiğiniz için teşekkür ederiz. "
             "Geçmiş olsun! {{clinic}}"),
            ("randevu-hatirlatma-en", "Appointment Reminder (EN)", T.APPOINTMENT, L.EN,
             "Dear {{owner_name}}, a reminder for {{pet_name}}'s appointment tomorrow {{date}} {{time}}. {{clinic}}"),
            ("asi-yaklasan-en", "Vaccine Due Soon (EN)", T.VACCINE, L.EN,
             "Dear {{owner_name}}, {{pet_name}}'s {{vaccine}} vaccine is due on {{date}}. "
             "Please call us to book. {{clinic}}"),
        ]
        for key, name, ttype, locale, body in catalog:
            MessageTemplate.objects.get_or_create(
                key=key, defaults={"name": name, "type": ttype, "locale": locale, "body": body}
            )

        # Not: VACCINE tipi kurallar TÜM koruyucu/tedavi kayıtlarını (aşı + parazit + ilaç)
        # tarar; metin kategoriye göre otomatik seçilir.
        for rname, rtype, offset, tkey in [
            ("Randevudan 1 gün önce", T.APPOINTMENT, 1, "randevu-hatirlatma"),
            ("Koruyucu: 7 gün önce", T.VACCINE, 7, "asi-yaklasan"),
            ("Koruyucu: aynı gün", T.VACCINE, 0, "asi-yaklasan"),
            ("Koruyucu: gecikme (1 gün sonra)", T.VACCINE, -1, "asi-geciken"),
        ]:
            ReminderRule.objects.get_or_create(
                name=rname, type=rtype, offset_days=offset,
                defaults={"template": MessageTemplate.objects.get(key=tkey)},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Bootstrap tamam: {Species.objects.count()} tür, "
            f"{VaccineDefinition.objects.count()} protokol (aşı/parazit/ilaç), "
            f"{MessageTemplate.objects.count()} şablon, {ServiceItem.objects.count()} hizmet."
        ))
