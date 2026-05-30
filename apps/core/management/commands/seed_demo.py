"""
Lokal demo için gerçekçi örnek veri yükler.

    python manage.py seed_demo            # ekler (idempotent: tekrar çalıştırılabilir)
    python manage.py seed_demo --reset    # önce demo verisini temizler

İleriki milestone'lar (aşı, muayene, kasa) bu komutu genişletecek.
Yönetici giriş: admin / admin123
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

SPECIES = [
    "Köpek", "Kedi", "Kuş", "At", "Hamster", "Kaplumbağa",
    "Sürüngen", "Koyun", "Keçi", "Tavşan", "Diğer",
]

OWNERS = [
    ("Ahmet", "Yılmaz", "0532 111 22 33", "Marmaris", "Merkez"),
    ("Elif", "Demir", "0505 444 55 66", "Marmaris", "Armutalan"),
    ("Mehmet", "Kaya", "0541 777 88 99", "Muğla", "Menteşe"),
    ("Zeynep", "Şahin", "0533 222 33 44", "Marmaris", "Beldibi"),
    ("Can", "Çelik", "0544 555 66 77", "Marmaris", "İçmeler"),
    ("Deniz", "Aydın", "0535 888 99 00", "Muğla", "Ortaca"),
]

PETS = [
    ("Boncuk", "Kedi", "Tekir", "female"),
    ("Karabaş", "Köpek", "Golden Retriever", "male"),
    ("Maviş", "Kuş", "Muhabbet Kuşu", "unknown"),
    ("Pamuk", "Kedi", "British Shorthair", "female"),
    ("Rex", "Köpek", "Alman Çoban", "male"),
    ("Şila", "Köpek", "Pomeranian", "female"),
    ("Limon", "Kuş", "Kanarya", "male"),
    ("Tarçın", "Tavşan", "Hollanda Lop", "female"),
    ("Duman", "Kedi", "Scottish Fold", "male"),
]


class Command(BaseCommand):
    help = "Lokal demo için örnek veri yükler."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Önce demo verisini sil.")

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.appointments.models import Appointment, AppointmentRequest
        from apps.billing.models import Charge, ChargeLine, Payment, ServiceItem
        from apps.core.models import ClinicSettings
        from apps.medical.models import (
            Examination,
            ExaminationTemplate,
            LabResult,
            Note,
            Operation,
            Prescription,
            PrescriptionItem,
        )
        from apps.owners.models import Owner
        from apps.patients.models import Patient, Species
        from apps.reminders.models import MessageTemplate, OutboundMessage, ReminderRule
        from apps.reminders.services import generate_reminders
        from apps.vaccines.models import VaccineDefinition, VaccineRecord

        if options["reset"]:
            self.stdout.write("Demo verisi temizleniyor…")
            Payment.objects.all().delete()
            ChargeLine.objects.all().delete()
            Charge.objects.all().delete()
            ServiceItem.objects.all().delete()
            OutboundMessage.objects.all().delete()
            ReminderRule.objects.all().delete()
            MessageTemplate.objects.all().delete()
            VaccineRecord.objects.all().delete()
            VaccineDefinition.objects.all().delete()
            Prescription.objects.all().delete()
            LabResult.objects.all().delete()
            Operation.objects.all().delete()
            Examination.objects.all().delete()
            ExaminationTemplate.objects.all().delete()
            Note.objects.all().delete()
            AppointmentRequest.objects.all().delete()
            Appointment.objects.all().delete()
            Patient.objects.all().delete()
            Owner.objects.all().delete()

        # Yönetici
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "first_name": "Klinik",
                "last_name": "Yöneticisi",
                "email": "info.rivaveteriner@gmail.com",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Yönetici oluşturuldu: admin / admin123"))

        # Klinik ayarları + logo (repodaki statik dosyadan, henüz yoksa)
        clinic = ClinicSettings.load()
        if not clinic.logo:
            from pathlib import Path

            from django.conf import settings as dj_settings
            from django.core.files import File

            logo_path = Path(dj_settings.BASE_DIR) / "static" / "img" / "riva-logo.jpg"
            if logo_path.exists():
                with open(logo_path, "rb") as f:
                    clinic.logo.save("riva-logo.jpg", File(f), save=True)

        # Türler
        species_map = {}
        for name in SPECIES:
            sp, _ = Species.objects.get_or_create(name=name)
            species_map[name] = sp

        vaccine_specs = [
            ("Kedi", "Karma", "8-9 haftalık", 365, 14, "Örnek başlangıç protokolüdür; klinik tarafından doğrulanmalıdır."),
            ("Kedi", "Kuduz", "12 haftalık", 365, 14, "Yasal zorunluluk ve güncel mevzuat klinik tarafından kontrol edilmelidir."),
            ("Köpek", "Karma", "6-8 haftalık", 365, 14, "Örnek başlangıç protokolüdür; klinik tarafından doğrulanmalıdır."),
            ("Köpek", "Kuduz", "12 haftalık", 365, 14, "Yasal zorunluluk ve güncel mevzuat klinik tarafından kontrol edilmelidir."),
        ]
        for species_name, vaccine_name, first_dose, repeat_days, reminder_days, description in vaccine_specs:
            VaccineDefinition.objects.get_or_create(
                species=species_map[species_name],
                name=vaccine_name,
                defaults={
                    "first_dose_age_text": first_dose,
                    "repeat_interval_days": repeat_days,
                    "reminder_offset_days": reminder_days,
                    "description": description,
                },
            )

        # Sahipler
        owners = []
        for first, last, phone, il, ilce in OWNERS:
            owner, _ = Owner.objects.get_or_create(
                first_name=first,
                last_name=last,
                defaults={
                    "phone": phone,
                    "il": il,
                    "ilce": ilce,
                    "contact_pref": Owner.ContactPref.WHATSAPP,
                    "kvkk_consent": True,
                    "kvkk_consent_at": timezone.now(),
                },
            )
            owners.append(owner)

        # Hayvanlar — sahiplere dağıt
        for i, (name, sp_name, breed, sex) in enumerate(PETS):
            owner = owners[i % len(owners)]
            Patient.objects.get_or_create(
                owner=owner,
                name=name,
                defaults={
                    "species": species_map.get(sp_name, species_map["Diğer"]),
                    "breed": breed,
                    "sex": sex,
                    "birth_date": date.today() - timedelta(days=random.randint(180, 2900)),
                    "microchip_no": f"TR{random.randint(100000000, 999999999)}",
                    "weight": round(random.uniform(2, 35), 1),
                    "neutered": random.choice(["yes", "no", "unknown"]),
                },
            )

        patients = list(Patient.objects.select_related("owner", "species").order_by("id"))
        now = timezone.localtime()
        appointment_specs = [
            (0, 0, 10, 0, Appointment.Type.GENERAL, Appointment.Status.CONFIRMED, "Genel kontrol"),
            (1, 1, 14, 30, Appointment.Type.VACCINE, Appointment.Status.CONFIRMED, "Karma aşı"),
            (2, 2, 11, 0, Appointment.Type.CONTROL, Appointment.Status.ARRIVED, "Kontrol muayenesi"),
            (3, 3, 16, 0, Appointment.Type.SURGERY, Appointment.Status.CONFIRMED, "Operasyon ön görüşme"),
            (4, -1, 15, 0, Appointment.Type.GENERAL, Appointment.Status.COMPLETED, "Tamamlanan randevu"),
            (5, -2, 9, 30, Appointment.Type.EMERGENCY, Appointment.Status.NO_SHOW, "Gelmedi"),
        ]
        for patient_index, day_offset, hour, minute, appt_type, status, note in appointment_specs:
            if not patients:
                break
            patient = patients[patient_index % len(patients)]
            starts_at = (now + timedelta(days=day_offset)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            Appointment.objects.get_or_create(
                patient=patient,
                starts_at=starts_at,
                defaults={
                    "owner": patient.owner,
                    "phone_snapshot": patient.owner.phone,
                    "duration_min": 30,
                    "type": appt_type,
                    "status": status,
                    "assigned_vet": admin,
                    "note": note,
                },
            )

        request_specs = [
            ("Ayşe Yıldız", "0530 222 11 00", "Mia", "Kedi", "Yarın öğleden sonra", "Aşı", "Karma aşı için uygun saat rica ediyor."),
            ("Burak Arslan", "0542 333 44 55", "Max", "Köpek", "Hafta sonu", "Kontrol", "Topallama şikayeti var."),
            ("Selin Koç", "0507 909 10 11", "Luna", "Kedi", "", "Genel muayene", "İlk kayıt ve genel kontrol."),
        ]
        for name, phone, pet_name, pet_species, requested_at, subject, message in request_specs:
            AppointmentRequest.objects.get_or_create(
                name=name,
                phone=phone,
                status=AppointmentRequest.NEW,
                defaults={
                    "pet_name": pet_name,
                    "pet_species": pet_species,
                    "requested_at": requested_at,
                    "subject": subject,
                    "message": message,
                    "source": AppointmentRequest.SOURCE_WEB,
                },
            )

        template_specs = [
            (
                "Genel Muayene",
                "Genel sağlık kontrolü",
                "İştah, su tüketimi, dışkılama ve davranış değişikliği sorgulandı.",
                "Genel durum stabil. Ateş, mukozalar, lenf nodları ve abdomen değerlendirildi.",
                "",
                "Klinik bulgulara göre takip.",
            ),
            (
                "Aşı Öncesi Kontrol",
                "Aşı öncesi değerlendirme",
                "Son 48 saatte kusma, ishal, halsizlik ve iştahsızlık sorgulandı.",
                "Aşıya engel akut bulgu saptanmadı.",
                "Aşı öncesi klinik kontrol",
                "Aşı sonrası 24 saat gözlem önerildi.",
            ),
            (
                "Kontrol Muayenesi",
                "Kontrol",
                "Önceki tedaviye yanıt ve ev gözlemleri alındı.",
                "Kontrol bulguları kaydedildi.",
                "",
                "Gerekirse tedavi güncellenecek.",
            ),
        ]
        templates = {}
        for name, complaint, anamnesis, findings, diagnosis, treatment_plan in template_specs:
            tpl, _ = ExaminationTemplate.objects.get_or_create(
                name=name,
                defaults={
                    "complaint": complaint,
                    "anamnesis": anamnesis,
                    "findings": findings,
                    "diagnosis": diagnosis,
                    "treatment_plan": treatment_plan,
                },
            )
            templates[name] = tpl

        exam_specs = [
            (0, "Genel Muayene", "Rutin kontrol", "Genel durum iyi.", "Sağlıklı", "Rutin takip.", 30),
            (1, "Aşı Öncesi Kontrol", "Aşı öncesi kontrol", "Ateş yok, genel durum stabil.", "Aşıya uygun", "Aşı uygulaması planlandı.", None),
            (2, "Kontrol Muayenesi", "Topallama kontrolü", "Sol arka ekstremitede hassasiyet azalmış.", "İyileşme süreci", "İlaçlara 3 gün devam.", 7),
        ]
        for patient_index, template_name, complaint, findings, diagnosis, treatment_plan, follow_days in exam_specs:
            if not patients:
                break
            patient = patients[patient_index % len(patients)]
            appointment = Appointment.objects.filter(patient=patient).order_by("-starts_at").first()
            exam, _ = Examination.objects.get_or_create(
                patient=patient,
                complaint=complaint,
                defaults={
                    "appointment": appointment,
                    "vet": admin,
                    "template": templates.get(template_name),
                    "anamnesis": templates.get(template_name).anamnesis if templates.get(template_name) else "",
                    "findings": findings,
                    "diagnosis": diagnosis,
                    "treatment_plan": treatment_plan,
                    "follow_up_date": (
                        timezone.localdate() + timedelta(days=follow_days) if follow_days else None
                    ),
                },
            )
            if patient_index == 0:
                Note.objects.get_or_create(
                    patient=patient,
                    body="Sahip evde iştah ve su tüketimini takip edecek.",
                    defaults={"created_by": admin, "updated_by": admin},
                )

        first_exam = Examination.objects.select_related("patient").order_by("id").first()
        if first_exam:
            prescription, _ = Prescription.objects.get_or_create(
                patient=first_exam.patient,
                examination=first_exam,
                defaults={
                    "vet": admin,
                    "notes": "İlaçlar yemek sonrası uygulanacak. Beklenmeyen reaksiyonda kliniği arayın.",
                },
            )
            item_specs = [
                ("Destek Vitamini", "1 ml", "Günde 1", "5 gün", "Ağızdan"),
                ("Probiyotik", "1 saşe", "Günde 1", "3 gün", "Mama ile"),
            ]
            for drug_name, dose, frequency, duration, note in item_specs:
                PrescriptionItem.objects.get_or_create(
                    prescription=prescription,
                    drug_name=drug_name,
                    defaults={
                        "dose": dose,
                        "frequency": frequency,
                        "duration": duration,
                        "note": note,
                    },
                )

            Operation.objects.get_or_create(
                patient=first_exam.patient,
                type="Diş taşı temizliği",
                date=timezone.localtime() - timedelta(days=12),
                defaults={
                    "vet": admin,
                    "anesthesia_info": "Kısa süreli sedasyon altında yapıldı.",
                    "drugs_used": "Sedasyon protokolü kayıt altına alındı.",
                    "result": "Diş yüzeyleri temizlendi, belirgin komplikasyon izlenmedi.",
                    "follow_up_date": timezone.localdate() + timedelta(days=30),
                    "post_op_instructions": "İlk 24 saat yumuşak mama önerildi.",
                },
            )
            LabResult.objects.get_or_create(
                patient=first_exam.patient,
                examination=first_exam,
                test_name="Hemogram",
                date=timezone.localdate(),
                defaults={
                    "result_note": "Referans dışı kritik bulgu saptanmadı.",
                },
            )

        vaccine_targets = [
            (0, "Karma", -340),
            (1, "Karma", -370),
            (3, "Kuduz", -350),
            (4, "Karma", -358),  # sonraki doz +7 gün → "yaklaşan" + aşı hatırlatma demosu
        ]
        for patient_index, vaccine_name, applied_offset in vaccine_targets:
            if not patients:
                break
            patient = patients[patient_index % len(patients)]
            definition = VaccineDefinition.objects.filter(
                species=patient.species, name=vaccine_name
            ).first()
            if not definition:
                continue
            applied_at = timezone.localdate() + timedelta(days=applied_offset)
            VaccineRecord.objects.get_or_create(
                patient=patient,
                vaccine_definition=definition,
                applied_at=applied_at,
                defaults={
                    "vet": admin,
                    "serial_lot": f"LOT{1000 + patient_index}",
                    "note": "Demo aşı kaydı.",
                },
            )

        # --- Hizmet/ürün + örnek işlemler ve tahsilatlar ---
        service_specs = [
            ("Genel Muayene", ServiceItem.Kind.SERVICE, 350),
            ("Karma Aşı", ServiceItem.Kind.SERVICE, 450),
            ("Kuduz Aşı", ServiceItem.Kind.SERVICE, 300),
            ("Mikroçip Uygulama", ServiceItem.Kind.SERVICE, 500),
            ("Mama (1.5 kg)", ServiceItem.Kind.PRODUCT, 600),
            ("Bit-Pire Damlası", ServiceItem.Kind.PRODUCT, 250),
        ]
        services = {}
        for name, kind, price in service_specs:
            obj, _ = ServiceItem.objects.get_or_create(
                name=name, defaults={"kind": kind, "default_price": price}
            )
            services[name] = obj

        if patients:
            charge_specs = [
                (0, [("Genel Muayene", 1), ("Mama (1.5 kg)", 1)], "paid"),
                (1, [("Karma Aşı", 1), ("Genel Muayene", 1)], "partial"),
                (2, [("Kuduz Aşı", 1)], "pending"),
            ]
            for patient_index, items, pay_state in charge_specs:
                patient = patients[patient_index % len(patients)]
                if Charge.objects.filter(owner=patient.owner, note=f"demo-{patient_index}").exists():
                    continue
                charge = Charge.objects.create(
                    owner=patient.owner, patient=patient, note=f"demo-{patient_index}"
                )
                for item_name, qty in items:
                    item = services[item_name]
                    ChargeLine.objects.create(
                        charge=charge, item=item, description=item.name,
                        qty=qty, unit_price=item.default_price,
                    )
                charge.recompute()
                if pay_state == "paid":
                    Payment.objects.create(
                        charge=charge, amount=charge.total, method=Payment.Method.CASH
                    )
                elif pay_state == "partial":
                    Payment.objects.create(
                        charge=charge, amount=(charge.total / 2).quantize(Decimal("0.01")),
                        method=Payment.Method.CARD,
                    )
                charge.recompute()

        # --- Mesaj şablonları + hatırlatma kuralları ---
        tpl_appt, _ = MessageTemplate.objects.get_or_create(
            key="randevu-1gun-tr",
            defaults={
                "name": "Randevu Hatırlatma (1 gün)",
                "type": MessageTemplate.Type.APPOINTMENT,
                "locale": MessageTemplate.Locale.TR,
                "body": (
                    "Sayın {{owner_name}}, {{pet_name}} için {{date}} {{time}} "
                    "randevunuzu hatırlatırız. {{clinic}}"
                ),
            },
        )
        tpl_vac, _ = MessageTemplate.objects.get_or_create(
            key="asi-7gun-tr",
            defaults={
                "name": "Aşı Hatırlatma (7 gün)",
                "type": MessageTemplate.Type.VACCINE,
                "locale": MessageTemplate.Locale.TR,
                "body": (
                    "Sayın {{owner_name}}, {{pet_name}} için {{vaccine}} aşısının "
                    "son tarihi {{date}}. Randevu için bizi arayabilirsiniz. {{clinic}}"
                ),
            },
        )
        MessageTemplate.objects.get_or_create(
            key="randevu-1gun-en",
            defaults={
                "name": "Appointment Reminder (1 day)",
                "type": MessageTemplate.Type.APPOINTMENT,
                "locale": MessageTemplate.Locale.EN,
                "body": (
                    "Dear {{owner_name}}, this is a reminder for {{pet_name}}'s appointment "
                    "on {{date}} {{time}}. {{clinic}}"
                ),
            },
        )
        ReminderRule.objects.get_or_create(
            name="Randevudan 1 gün önce",
            type=MessageTemplate.Type.APPOINTMENT,
            offset_days=1,
            defaults={"template": tpl_appt},
        )
        ReminderRule.objects.get_or_create(
            name="Aşıdan 7 gün önce",
            type=MessageTemplate.Type.VACCINE,
            offset_days=7,
            defaults={"template": tpl_vac},
        )

        reminder_result = generate_reminders()

        self.stdout.write(self.style.SUCCESS(
            f"Tamam: {Owner.objects.count()} sahip, {Patient.objects.count()} hayvan, "
            f"{Species.objects.count()} tür, {Appointment.objects.count()} randevu, "
            f"{AppointmentRequest.objects.filter(status=AppointmentRequest.NEW).count()} yeni talep, "
            f"{Examination.objects.count()} muayene, {Prescription.objects.count()} reçete, "
            f"{Operation.objects.count()} operasyon, {LabResult.objects.count()} lab sonucu, "
            f"{VaccineRecord.objects.count()} aşı kaydı, "
            f"{Charge.objects.count()} işlem, {Payment.objects.count()} tahsilat, "
            f"{OutboundMessage.objects.count()} hatırlatma ({reminder_result['total']} yeni)."
        ))
