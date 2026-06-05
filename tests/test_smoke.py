"""M0–M2 smoke testleri: kritik sayfalar render oluyor mu, temel CRUD çalışıyor mu."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment, AppointmentRequest
from apps.medical.models import Examination, LabResult, Note, Operation, Prescription
from apps.owners.models import Owner
from apps.patients.models import Patient, Species
from apps.vaccines.models import VaccineDefinition, VaccineRecord


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username="tester", password="pw12345!", email="t@example.com", role=User.Role.ADMIN
    )
    return user


@pytest.fixture
def auth_client(client, admin_user):
    client.force_login(admin_user)
    return client


def test_login_page_renders(client, db):
    resp = client.get(reverse("accounts:login"))
    assert resp.status_code == 200
    assert "Giriş" in resp.content.decode()


def test_dashboard_requires_login(client, db):
    resp = client.get(reverse("core:dashboard"))
    assert resp.status_code == 302
    assert "/giris/" in resp.url


def test_dashboard_renders(auth_client):
    resp = auth_client.get(reverse("core:dashboard"))
    assert resp.status_code == 200
    assert "Panel" in resp.content.decode()


def test_owner_list_and_create(auth_client, db):
    assert auth_client.get(reverse("owners:list")).status_code == 200
    resp = auth_client.post(
        reverse("owners:create"),
        {
            "first_name": "Test",
            "last_name": "Sahip",
            "phone": "0500 000 00 00",
            "contact_pref": "whatsapp",
            "kvkk_consent": "on",
        },
    )
    assert resp.status_code == 302
    owner = Owner.objects.get(first_name="Test")
    assert owner.kvkk_consent_at is not None  # KVKK damgası
    assert auth_client.get(reverse("owners:detail", args=[owner.pk])).status_code == 200


def test_patient_create_and_detail(auth_client, db):
    owner = Owner.objects.create(first_name="A", last_name="B", phone="0501")
    sp = Species.objects.create(name="Kedi")
    resp = auth_client.post(
        reverse("patients:create"),
        {"owner": owner.pk, "name": "Minnoş", "species": sp.pk, "sex": "female", "neutered": "unknown"},
    )
    assert resp.status_code == 302
    patient = Patient.objects.get(name="Minnoş")
    assert auth_client.get(reverse("patients:detail", args=[patient.pk])).status_code == 200


def test_search_page(auth_client, db):
    Owner.objects.create(first_name="Arama", last_name="Test", phone="0555 123 45 67")
    resp = auth_client.get(reverse("core:search"), {"q": "Arama"})
    assert resp.status_code == 200
    assert "Arama" in resp.content.decode()


def test_audit_log_written_on_create(auth_client, db):
    from apps.core.models import AuditLog

    auth_client.post(
        reverse("owners:create"),
        {"first_name": "Denetim", "last_name": "Kaydı", "phone": "0507", "contact_pref": "phone"},
    )
    assert AuditLog.objects.filter(model_label="owners.Owner", action="create").exists()


def test_appointment_calendar_events_and_create(auth_client, admin_user, db):
    owner = Owner.objects.create(first_name="Randevu", last_name="Sahibi", phone="0502")
    species = Species.objects.create(name="Köpek")
    patient = Patient.objects.create(owner=owner, name="Dost", species=species)
    starts_at = timezone.localtime().replace(hour=10, minute=0, second=0, microsecond=0)
    appt = Appointment.objects.create(
        owner=owner,
        patient=patient,
        starts_at=starts_at,
        assigned_vet=admin_user,
        type=Appointment.Type.GENERAL,
        status=Appointment.Status.CONFIRMED,
    )

    assert auth_client.get(reverse("appointments:calendar")).status_code == 200
    events = auth_client.get(
        reverse("appointments:events"),
        {
            "start": (starts_at - timedelta(days=1)).isoformat(),
            "end": (starts_at + timedelta(days=1)).isoformat(),
        },
    )
    assert events.status_code == 200
    assert any(item["id"] == appt.pk for item in events.json())

    new_start = (starts_at + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    resp = auth_client.post(
        reverse("appointments:create"),
        {
            "patient": patient.pk,
            "starts_at": new_start,
            "duration_min": 30,
            "type": Appointment.Type.CONTROL,
            "status": Appointment.Status.CONFIRMED,
            "assigned_vet": admin_user.pk,
            "note": "Smoke test",
        },
    )
    assert resp.status_code == 302
    created = Appointment.objects.get(note="Smoke test")
    assert created.owner == owner
    assert created.phone_snapshot == owner.phone


def test_appointment_status_and_request_flow(auth_client, db):
    owner = Owner.objects.create(first_name="Talep", last_name="Sahibi", phone="0503")
    species = Species.objects.create(name="Kedi")
    patient = Patient.objects.create(owner=owner, name="Tekir", species=species)
    appt = Appointment.objects.create(
        owner=owner,
        patient=patient,
        starts_at=timezone.now() + timedelta(days=1),
        status=Appointment.Status.REQUESTED,
    )

    resp = auth_client.post(
        reverse("appointments:set_status", args=[appt.pk]),
        {"status": Appointment.Status.ARRIVED},
    )
    assert resp.status_code == 302
    appt.refresh_from_db()
    assert appt.status == Appointment.Status.ARRIVED

    payload = {
        "name": "Web Talep",
        "phone": "0555 111 22 33",
        "pet_name": "Pamuk",
        "pet_species": "Kedi",
        "requested_at": "Yarın 14:00",
        "subject": "Aşı",
        "message": "Uygun saat rica ederim.",
    }
    api_resp = auth_client.post(
        reverse("appointments:api_create_request"),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert api_resp.status_code == 200
    assert AppointmentRequest.objects.filter(name="Web Talep", status=AppointmentRequest.NEW).exists()
    assert auth_client.get(reverse("appointments:request_list")).status_code == 200


def test_examination_create_detail_and_patient_timeline(auth_client, admin_user, db):
    owner = Owner.objects.create(first_name="Muayene", last_name="Sahibi", phone="0504")
    species = Species.objects.create(name="Kuş")
    patient = Patient.objects.create(owner=owner, name="Mavi", species=species)

    assert auth_client.get(reverse("medical:examination_list")).status_code == 200
    resp = auth_client.post(
        reverse("medical:examination_create"),
        {
            "patient": patient.pk,
            "vet": admin_user.pk,
            "complaint": "Halsizlik",
            "anamnesis": "İştah azalmış.",
            "findings": "Genel durum orta.",
            "diagnosis": "Üst solunum yolu şüphesi",
            "treatment_plan": "Destek tedavisi ve takip.",
            "notes": "Kontrol önerildi.",
            "follow_up_date": (timezone.localdate() + timedelta(days=7)).isoformat(),
        },
    )
    assert resp.status_code == 302
    exam = Examination.objects.get(patient=patient)
    detail = auth_client.get(reverse("medical:examination_detail", args=[exam.pk]))
    assert detail.status_code == 200
    assert "Üst solunum yolu" in detail.content.decode()

    patient_detail = auth_client.get(reverse("patients:detail", args=[patient.pk]))
    body = patient_detail.content.decode()
    assert patient_detail.status_code == 200
    assert "Muayeneler" in body
    assert "Halsizlik" in body


def test_prescription_create_detail_and_pdf(auth_client, admin_user, db):
    owner = Owner.objects.create(first_name="Reçete", last_name="Sahibi", phone="0508")
    species = Species.objects.create(name="Tavşan")
    patient = Patient.objects.create(owner=owner, name="Tarçın", species=species)
    exam = Examination.objects.create(
        patient=patient,
        vet=admin_user,
        complaint="İştahsızlık",
        diagnosis="Sindirim hassasiyeti",
    )

    resp = auth_client.post(
        reverse("medical:prescription_create"),
        {
            "patient": patient.pk,
            "examination": exam.pk,
            "vet": admin_user.pk,
            "notes": "Bol su ile takip.",
            "items-TOTAL_FORMS": "3",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-drug_name": "Probiyotik",
            "items-0-dose": "1 saşe",
            "items-0-frequency": "Günde 1",
            "items-0-duration": "3 gün",
            "items-0-note": "Mama ile",
            "items-1-drug_name": "",
            "items-1-dose": "",
            "items-1-frequency": "",
            "items-1-duration": "",
            "items-1-note": "",
            "items-2-drug_name": "",
            "items-2-dose": "",
            "items-2-frequency": "",
            "items-2-duration": "",
            "items-2-note": "",
        },
    )
    assert resp.status_code == 302
    prescription = Prescription.objects.get(patient=patient)
    assert prescription.items.filter(drug_name="Probiyotik").exists()

    detail = auth_client.get(reverse("medical:prescription_detail", args=[prescription.pk]))
    assert detail.status_code == 200
    assert "Probiyotik" in detail.content.decode()

    pdf = auth_client.get(reverse("medical:prescription_pdf", args=[prescription.pk]))
    assert pdf.status_code == 200
    assert pdf["Content-Type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_operation_lab_and_note_flows(auth_client, admin_user, db):
    owner = Owner.objects.create(first_name="Tıbbi", last_name="Takip", phone="0509")
    species = Species.objects.create(name="Hamster")
    patient = Patient.objects.create(owner=owner, name="Fındık", species=species)
    exam = Examination.objects.create(patient=patient, vet=admin_user, complaint="Kontrol")

    operation_resp = auth_client.post(
        reverse("medical:operation_create"),
        {
            "patient": patient.pk,
            "date": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "vet": admin_user.pk,
            "type": "Küçük yara bakımı",
            "anesthesia_info": "Sedasyon gerekmedi.",
            "drugs_used": "Lokal antiseptik",
            "result": "Yara temizlendi.",
            "notes": "",
            "follow_up_date": (timezone.localdate() + timedelta(days=5)).isoformat(),
            "post_op_instructions": "Yalama engellenecek.",
        },
    )
    assert operation_resp.status_code == 302
    operation = Operation.objects.get(patient=patient)
    assert auth_client.get(reverse("medical:operation_detail", args=[operation.pk])).status_code == 200

    lab_resp = auth_client.post(
        reverse("medical:lab_result_create"),
        {
            "patient": patient.pk,
            "examination": exam.pk,
            "test_name": "Hemogram",
            "date": timezone.localdate().isoformat(),
            "result_note": "Kritik bulgu yok.",
        },
    )
    assert lab_resp.status_code == 302
    lab = LabResult.objects.get(patient=patient)
    assert auth_client.get(reverse("medical:lab_result_detail", args=[lab.pk])).status_code == 200

    note_resp = auth_client.post(
        reverse("medical:note_create"),
        {"patient": patient.pk, "body": "Evde iştah takibi yapılacak."},
    )
    assert note_resp.status_code == 302
    note = Note.objects.get(patient=patient)
    assert auth_client.get(reverse("medical:note_detail", args=[note.pk])).status_code == 200

    body = auth_client.get(reverse("patients:detail", args=[patient.pk])).content.decode()
    assert "Küçük yara bakımı" in body
    assert "Hemogram" in body
    assert "Evde iştah" in body


def test_vaccine_protocol_record_and_due_lists(auth_client, admin_user, db):
    owner = Owner.objects.create(first_name="Aşı", last_name="Sahibi", phone="0510")
    species = Species.objects.create(name="Kedi")
    patient = Patient.objects.create(owner=owner, name="Pamuk", species=species)
    definition = VaccineDefinition.objects.create(
        species=species,
        name="Karma",
        first_dose_age_text="8 haftalık",
        repeat_interval_days=365,
        reminder_offset_days=14,
        description="Test protokolü",
    )

    assert auth_client.get(reverse("vaccines:protocols")).status_code == 200
    resp = auth_client.post(
        reverse("vaccines:record_create"),
        {
            "patient": patient.pk,
            "vaccine_definition": definition.pk,
            "vaccine_name": "",
            "applied_at": timezone.localdate().isoformat(),
            "next_due_at": "",
            "vet": admin_user.pk,
            "serial_lot": "TST-001",
            "expiry_date": "",
            "note": "Smoke test aşı kaydı",
        },
    )
    assert resp.status_code == 302
    record = VaccineRecord.objects.get(patient=patient)
    assert record.vaccine_name == "Karma"
    assert record.next_due_at == timezone.localdate() + timedelta(days=365)
    assert auth_client.get(reverse("vaccines:record_detail", args=[record.pk])).status_code == 200

    overdue = VaccineRecord.objects.create(
        patient=patient,
        vaccine_name="Geciken Test",
        applied_at=timezone.localdate() - timedelta(days=400),
        next_due_at=timezone.localdate() - timedelta(days=35),
        vet=admin_user,
    )
    upcoming = VaccineRecord.objects.create(
        patient=patient,
        vaccine_name="Yaklaşan Test",
        applied_at=timezone.localdate() - timedelta(days=350),
        next_due_at=timezone.localdate() + timedelta(days=10),
        vet=admin_user,
    )

    upcoming_page = auth_client.get(reverse("vaccines:upcoming"))
    assert upcoming_page.status_code == 200
    assert upcoming.display_name in upcoming_page.content.decode()
    overdue_page = auth_client.get(reverse("vaccines:overdue"))
    assert overdue_page.status_code == 200
    assert overdue.display_name in overdue_page.content.decode()

    patient_detail = auth_client.get(reverse("patients:detail", args=[patient.pk]))
    body = patient_detail.content.decode()
    assert patient_detail.status_code == 200
    assert "Aşılar" in body
    assert "Smoke test aşı kaydı" in body


def test_vaccine_certificate_and_history_pdf(auth_client, admin_user, db):
    owner = Owner.objects.create(first_name="Sertifika", last_name="Sahibi", phone="0511")
    species = Species.objects.create(name="Köpek")
    patient = Patient.objects.create(owner=owner, name="Çakıl", species=species)
    record = VaccineRecord.objects.create(
        patient=patient,
        vaccine_name="Kuduz",
        applied_at=timezone.localdate(),
        next_due_at=timezone.localdate() + timedelta(days=365),
        vet=admin_user,
        serial_lot="LOT-9",
    )

    cert = auth_client.get(reverse("vaccines:certificate_pdf", args=[record.pk]))
    assert cert.status_code == 200
    assert cert["Content-Type"] == "application/pdf"
    assert cert.content.startswith(b"%PDF")

    history = auth_client.get(reverse("vaccines:history_pdf", args=[patient.pk]))
    assert history.status_code == 200
    assert history["Content-Type"] == "application/pdf"
    assert history.content.startswith(b"%PDF")


def test_reminder_generation_and_queue_flow(auth_client, admin_user, db):
    from apps.reminders.models import MessageTemplate, OutboundMessage, ReminderRule
    from apps.reminders.services import generate_reminders

    owner = Owner.objects.create(
        first_name="Hatırlatma", last_name="Sahibi", phone="0532 000 11 22",
        contact_pref=Owner.ContactPref.WHATSAPP,
    )
    species = Species.objects.create(name="Köpek")
    patient = Patient.objects.create(owner=owner, name="Paşa", species=species)
    Appointment.objects.create(
        owner=owner, patient=patient,
        starts_at=timezone.now() + timedelta(days=1),
        status=Appointment.Status.CONFIRMED, assigned_vet=admin_user,
    )
    tpl = MessageTemplate.objects.create(
        key="t-appt", name="Randevu", type=MessageTemplate.Type.APPOINTMENT,
        body="Sayın {{owner_name}}, {{pet_name}} randevusu {{date}} {{time}}.",
    )
    ReminderRule.objects.create(
        name="1 gün önce", type=MessageTemplate.Type.APPOINTMENT, offset_days=1, template=tpl
    )

    result = generate_reminders()
    assert result["appointment"] == 1
    msg = OutboundMessage.objects.get(owner=owner)
    assert "Paşa" in msg.body and msg.wa_link.startswith("https://wa.me/")
    assert msg.status == OutboundMessage.PENDING

    # idempotent: ikinci kez üretmez
    assert generate_reminders()["total"] == 0

    # kuyruk + işaretleme
    assert auth_client.get(reverse("reminders:queue")).status_code == 200
    assert auth_client.get(reverse("reminders:templates")).status_code == 200
    resp = auth_client.post(reverse("reminders:mark_sent", args=[msg.pk]))
    assert resp.status_code == 302
    msg.refresh_from_db()
    assert msg.status == OutboundMessage.SENT and msg.sent_at is not None


def test_reminder_skips_no_contact_pref(db):
    from apps.reminders.models import MessageTemplate, ReminderRule
    from apps.reminders.services import generate_reminders

    owner = Owner.objects.create(
        first_name="İletişim", last_name="Yok", phone="0533 1",
        contact_pref=Owner.ContactPref.NONE,
    )
    species = Species.objects.create(name="Kedi")
    patient = Patient.objects.create(owner=owner, name="Sessiz", species=species)
    Appointment.objects.create(
        owner=owner, patient=patient,
        starts_at=timezone.now() + timedelta(days=1), status=Appointment.Status.CONFIRMED,
    )
    tpl = MessageTemplate.objects.create(
        key="t2", name="R", type=MessageTemplate.Type.APPOINTMENT, body="{{pet_name}}"
    )
    ReminderRule.objects.create(
        name="1g", type=MessageTemplate.Type.APPOINTMENT, offset_days=1, template=tpl
    )
    assert generate_reminders()["appointment"] == 0  # iletişim tercihi 'none' → atlanır


def test_billing_charge_payment_and_balance(auth_client, db):
    from decimal import Decimal

    from apps.billing.models import Charge, Payment, ServiceItem

    owner = Owner.objects.create(first_name="Kasa", last_name="Sahibi", phone="0540 12 34")
    species = Species.objects.create(name="Köpek")
    patient = Patient.objects.create(owner=owner, name="Bonus", species=species)
    svc = ServiceItem.objects.create(name="Genel Muayene", default_price=Decimal("350.00"))

    # İşlem + 2 satır (biri hizmetten fiyat türetir)
    resp = auth_client.post(
        reverse("billing:charge_create"),
        {
            "owner": owner.pk,
            "patient": patient.pk,
            "note": "Test işlem",
            "lines-TOTAL_FORMS": "4",
            "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "0",
            "lines-MAX_NUM_FORMS": "1000",
            "lines-0-item": svc.pk,
            "lines-0-description": "",
            "lines-0-qty": "1",
            "lines-0-unit_price": "",
            "lines-1-item": "",
            "lines-1-description": "Tırnak kesimi",
            "lines-1-qty": "1",
            "lines-1-unit_price": "150",
            "lines-2-item": "", "lines-2-description": "", "lines-2-qty": "", "lines-2-unit_price": "",
            "lines-3-item": "", "lines-3-description": "", "lines-3-qty": "", "lines-3-unit_price": "",
        },
    )
    assert resp.status_code == 302
    charge = Charge.objects.get(note="Test işlem")
    assert charge.total == Decimal("500.00")  # 350 (item) + 150
    assert charge.status == Charge.PENDING

    # Kısmi tahsilat
    auth_client.post(
        reverse("billing:charge_payment", args=[charge.pk]),
        {"charge": charge.pk, "amount": "200", "method": "cash",
         "paid_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M")},
    )
    charge.refresh_from_db()
    assert charge.status == Charge.PARTIAL
    assert charge.balance == Decimal("300.00")
    assert owner.balance == 300.0  # Owner.balance (Σtotal − Σpayment)

    # Kalanı kapat
    auth_client.post(
        reverse("billing:charge_payment", args=[charge.pk]),
        {"charge": charge.pk, "amount": "300", "method": "card",
         "paid_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M")},
    )
    charge.refresh_from_db()
    assert charge.status == Charge.PAID
    assert charge.balance == Decimal("0.00")

    assert auth_client.get(reverse("billing:index")).status_code == 200
    assert auth_client.get(reverse("billing:charge_detail", args=[charge.pk])).status_code == 200
    assert auth_client.get(reverse("billing:e_invoice_sim", args=[charge.pk])).status_code == 200
    assert Payment.objects.filter(charge=charge).count() == 2


def test_reports_page(auth_client, admin_user, db):
    owner = Owner.objects.create(first_name="Rapor", last_name="Sahibi", phone="0541 00 00")
    species = Species.objects.create(name="Kedi")
    patient = Patient.objects.create(owner=owner, name="Zeytin", species=species)
    Appointment.objects.create(
        owner=owner, patient=patient,
        starts_at=timezone.now(), status=Appointment.Status.CONFIRMED,
    )
    resp = auth_client.get(reverse("reports:index"))
    assert resp.status_code == 200
    assert "Raporlar" in resp.content.decode()
    # Tarih parametresi
    assert auth_client.get(
        reverse("reports:index"), {"date": timezone.localdate().isoformat()}
    ).status_code == 200


def test_patient_options_filtered_by_owner(auth_client, db):
    o1 = Owner.objects.create(first_name="Sahip", last_name="Bir", phone="0561")
    o2 = Owner.objects.create(first_name="Sahip", last_name="İki", phone="0562")
    sp = Species.objects.create(name="Kedi")
    p1 = Patient.objects.create(owner=o1, name="Tekir", species=sp)
    p2 = Patient.objects.create(owner=o2, name="Minnoş", species=sp)

    # o1 seçilince sadece o1'in hayvanı dönmeli
    resp = auth_client.get(reverse("patients:options"), {"owner": o1.pk})
    body = resp.content.decode()
    assert resp.status_code == 200
    assert "Tekir" in body and "Minnoş" not in body
    assert f'value="{p1.pk}"' in body and f'value="{p2.pk}"' not in body

    # owner verilmezse hayvan listelenmez (sadece placeholder)
    empty = auth_client.get(reverse("patients:options")).content.decode()
    assert "Tekir" not in empty and "Minnoş" not in empty


def test_appointment_reminder_enabled_controls_generation(db, admin_user):
    from apps.reminders.models import MessageTemplate, ReminderRule
    from apps.reminders.services import generate_reminders

    owner = Owner.objects.create(first_name="Hat", last_name="Kapalı", phone="0570",
                                 contact_pref=Owner.ContactPref.WHATSAPP)
    sp = Species.objects.create(name="Köpek")
    pet = Patient.objects.create(owner=owner, name="Bek", species=sp)
    tpl = MessageTemplate.objects.create(key="t-x", name="R", type=MessageTemplate.Type.APPOINTMENT,
                                         body="{{pet_name}}")
    ReminderRule.objects.create(name="1g", type=MessageTemplate.Type.APPOINTMENT, offset_days=1, template=tpl)
    # reminder_enabled=False → üretilmemeli
    Appointment.objects.create(owner=owner, patient=pet, starts_at=timezone.now() + timedelta(days=1),
                               status=Appointment.Status.CONFIRMED, reminder_enabled=False)
    assert generate_reminders()["appointment"] == 0
    # reminder_enabled=True → üretilmeli
    Appointment.objects.create(owner=owner, patient=pet, starts_at=timezone.now() + timedelta(days=1),
                               status=Appointment.Status.CONFIRMED, reminder_enabled=True)
    assert generate_reminders()["appointment"] == 1


def test_vaccine_series_next_due_and_followup_appointment(auth_client, admin_user, db):
    from apps.vaccines.models import VaccineDefinition, VaccineRecord

    owner = Owner.objects.create(first_name="Seri", last_name="Vak", phone="0571")
    sp = Species.objects.create(name="Köpek")
    pet = Patient.objects.create(owner=owner, name="Çomar", species=sp)
    d = VaccineDefinition.objects.create(name="Yavru Karma", species=sp, series_doses=2,
                                         series_interval_days=21, repeat_interval_days=365)
    # Doz 1 → seri aralığı (+21)
    r1 = VaccineRecord.objects.create(patient=pet, vaccine_definition=d, applied_at=timezone.localdate())
    assert (r1.next_due_at - timezone.localdate()).days == 21
    # Doz 2 → seri bitti, rapel (+365)
    r2 = VaccineRecord.objects.create(patient=pet, vaccine_definition=d,
                                      applied_at=timezone.localdate() + timedelta(days=21))
    assert (r2.next_due_at - (timezone.localdate() + timedelta(days=21))).days == 365

    # Apply view: create_followup → planlı randevu oluşur
    from apps.appointments.models import Appointment as Appt
    n0 = Appt.objects.filter(patient=pet, type=Appt.Type.VACCINE).count()
    resp = auth_client.post(reverse("vaccines:record_create"), {
        "patient": pet.pk, "vaccine_definition": d.pk, "vaccine_name": "",
        "applied_at": timezone.localdate().isoformat(), "next_due_at": "", "vet": admin_user.pk,
        "serial_lot": "", "expiry_date": "", "note": "", "create_followup": "on",
    })
    assert resp.status_code == 302
    assert Appt.objects.filter(patient=pet, type=Appt.Type.VACCINE).count() == n0 + 1


def test_definition_options_filtered_by_species(auth_client, db):
    from apps.vaccines.models import VaccineDefinition

    cat = Species.objects.create(name="Kedi")
    dog = Species.objects.create(name="Köpek")
    o = Owner.objects.create(first_name="A", last_name="B", phone="0572")
    cat_pet = Patient.objects.create(owner=o, name="Kedicik", species=cat)
    VaccineDefinition.objects.create(name="Kedi Karma", species=cat)
    VaccineDefinition.objects.create(name="Köpek Karma", species=dog)
    body = auth_client.get(reverse("vaccines:definition_options"), {"patient": cat_pet.pk}).content.decode()
    assert "Kedi Karma" in body and "Köpek Karma" not in body


def test_template_render_endpoint_and_prefill(auth_client, db):
    from apps.reminders.models import MessageTemplate

    owner = Owner.objects.create(first_name="Şablon", last_name="Test", phone="0573")
    sp = Species.objects.create(name="Kedi")
    pet = Patient.objects.create(owner=owner, name="Boncuk", species=sp)
    MessageTemplate.objects.create(key="tesekkur", name="Teşekkür", type=MessageTemplate.Type.GENERAL,
                                   body="Sayın {{owner_name}}, {{pet_name}} için teşekkürler. {{clinic}}")
    # Render endpoint: owner/patient yer tutucuları dolar
    r = auth_client.get(reverse("reminders:render_template"),
                        {"template": MessageTemplate.objects.get(key="tesekkur").pk,
                         "owner": owner.pk, "patient": pet.pk})
    text = r.content.decode()
    assert r.status_code == 200 and "Şablon Test" in text and "Boncuk" in text
    # Manuel form: template_key ile body önceden dolu gelir
    m = auth_client.get(reverse("reminders:manual_create"),
                        {"owner": owner.pk, "patient": pet.pk, "template_key": "tesekkur"})
    assert m.status_code == 200 and "Boncuk için teşekkürler" in m.content.decode()


def test_reminder_state_based_template_selection(db):
    from apps.reminders.models import MessageTemplate, ReminderRule
    from apps.reminders.services import generate_reminders
    from apps.vaccines.models import VaccineRecord

    owner = Owner.objects.create(first_name="Durum", last_name="Test", phone="0574",
                                 contact_pref=Owner.ContactPref.WHATSAPP)
    sp = Species.objects.create(name="Köpek")
    pet = Patient.objects.create(owner=owner, name="Karabaş", species=sp)
    MessageTemplate.objects.create(key="asi-yaklasan", name="Yaklaşan", type=MessageTemplate.Type.VACCINE,
                                   body="YAKLASAN {{vaccine}}")
    MessageTemplate.objects.create(key="asi-geciken", name="Geciken", type=MessageTemplate.Type.VACCINE,
                                   body="GECIKEN {{vaccine}}")
    up = VaccineRecord.objects.create(patient=pet, vaccine_name="Karma",
                                      applied_at=timezone.localdate() - timedelta(days=358),
                                      next_due_at=timezone.localdate() + timedelta(days=7))
    od = VaccineRecord.objects.create(patient=pet, vaccine_name="Kuduz",
                                      applied_at=timezone.localdate() - timedelta(days=366),
                                      next_due_at=timezone.localdate() - timedelta(days=1))
    ReminderRule.objects.create(name="yaklasan", type=MessageTemplate.Type.VACCINE, offset_days=7,
                                template=MessageTemplate.objects.get(key="asi-yaklasan"))
    ReminderRule.objects.create(name="geciken", type=MessageTemplate.Type.VACCINE, offset_days=-1,
                                template=MessageTemplate.objects.get(key="asi-geciken"))
    generate_reminders()
    assert up.messages.first().body.startswith("YAKLASAN")
    assert od.messages.first().body.startswith("GECIKEN")


def test_walk_in_to_checkout_end_to_end(auth_client, admin_user, db):
    """Klinik akışı: Hızlı Kabul → Muayene → Hesap Kapat."""
    from apps.appointments.models import Appointment
    from apps.billing.models import Charge, ServiceItem
    from apps.medical.models import Examination

    sp = Species.objects.create(name="Kedi")
    # 1) Hızlı kabul: yeni sahip + yeni hayvan
    resp = auth_client.post(reverse("appointments:walk_in"), {
        "owner": "", "new_owner_first": "Akış", "new_owner_last": "Test", "new_owner_phone": "0566 10 20",
        "patient": "", "new_pet_name": "Pati", "new_pet_species": sp.pk, "new_pet_sex": "female",
        "type": "general", "complaint": "Kusma", "vet": admin_user.pk,
    })
    assert resp.status_code == 302
    owner = Owner.objects.get(first_name="Akış")
    appt = Appointment.objects.get(owner=owner)
    assert appt.status == Appointment.Status.IN_EXAM
    assert appt.source == Appointment.Source.WALK_IN
    assert appt.reminder_enabled is False
    exam = Examination.objects.get(appointment=appt)
    assert f"/muayeneler/{exam.pk}/" in resp.url

    # 2) Muayene komuta ekranı render
    body = auth_client.get(reverse("medical:examination_detail", args=[exam.pk])).content.decode()
    assert "Hesap Kapat" in body

    # 3) Hesap kapat (tek ekran) — kısmi ödeme
    ServiceItem.objects.create(name="Genel Muayene", default_price=300)
    resp2 = auth_client.post(reverse("billing:checkout", args=[exam.pk]), {
        "lines-TOTAL_FORMS": "4", "lines-INITIAL_FORMS": "0", "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
        "lines-0-item": "", "lines-0-description": "Genel Muayene", "lines-0-qty": "1", "lines-0-unit_price": "400",
        "lines-1-item": "", "lines-1-description": "", "lines-1-qty": "", "lines-1-unit_price": "",
        "lines-2-item": "", "lines-2-description": "", "lines-2-qty": "", "lines-2-unit_price": "",
        "lines-3-item": "", "lines-3-description": "", "lines-3-qty": "", "lines-3-unit_price": "",
        "amount": "150", "method": "cash", "paid_at": "",
    })
    assert resp2.status_code == 302
    charge = Charge.objects.get(examination=exam)
    assert charge.total == __import__("decimal").Decimal("400.00")
    assert charge.status == Charge.PARTIAL  # 150 < 400
    appt.refresh_from_db()
    assert appt.status == Appointment.Status.COMPLETED

    # 4) İkinci kez checkout → yeni charge oluşmaz
    auth_client.get(reverse("billing:checkout", args=[exam.pk]))
    assert Charge.objects.filter(examination=exam).count() == 1


def test_walk_in_owner_live_search_finds_owner(auth_client, db):
    """Hızlı kabul'deki canlı sahip araması mevcut sahibi bulmalı (param adı endpoint ile uyumlu)."""
    import re

    Owner.objects.create(first_name="Arama", last_name="Hedef", phone="0599 88 77")
    html = auth_client.get(reverse("appointments:walk_in")).content.decode()
    # owner-field'ı dolduran arama input'unu bul ve gönderdiği param adını çıkar
    tag = re.search(r'<input[^>]*hx-target="#owner-field"[^>]*>', html)
    assert tag, "Hızlı kabul'de sahip arama input'u bulunamadı"
    param = re.search(r'name="([^"]+)"', tag.group(0)).group(1)
    # Tarayıcı bu input değerini ?<param>= olarak gönderir → endpoint sahibi bulmalı
    res = auth_client.get(reverse("owners:options"), {param: "Arama"}).content.decode()
    assert "Arama Hedef" in res, f"Arama '{param}' parametresiyle sahibi bulamadı"


def test_appointment_reschedule_drag(auth_client, admin_user, db):
    """Takvimde sürükle-bırak → randevu tarihi/süresi güncellenir."""
    from apps.appointments.models import Appointment

    owner = Owner.objects.create(first_name="Takvim", last_name="Test", phone="0533 9")
    sp = Species.objects.create(name="Kedi")
    pet = Patient.objects.create(owner=owner, name="Mia", species=sp)
    appt = Appointment.objects.create(
        owner=owner, patient=pet, starts_at=timezone.now(), duration_min=30,
    )
    new_start = (timezone.now() + timedelta(days=2)).replace(microsecond=0)
    resp = auth_client.post(reverse("appointments:reschedule"), {
        "id": appt.pk,
        "start": new_start.isoformat(),
        "end": (new_start + timedelta(minutes=45)).isoformat(),
    })
    assert resp.status_code == 200 and resp.json()["ok"] is True
    appt.refresh_from_db()
    assert abs((appt.starts_at - new_start).total_seconds()) < 60
    assert appt.duration_min == 45
    # takvim sayfası render
    assert auth_client.get(reverse("appointments:calendar")).status_code == 200


def test_start_exam_from_appointment(auth_client, admin_user, db):
    """Randevudan 'Muayeneye Al': durum in_exam + muayene açılır, ikinci kez tekrar açmaz."""
    from apps.appointments.models import Appointment
    from apps.medical.models import Examination

    owner = Owner.objects.create(first_name="Randevulu", last_name="Hasta", phone="0555 00 11")
    sp = Species.objects.create(name="Kedi")
    pet = Patient.objects.create(owner=owner, name="Tekir", species=sp)
    appt = Appointment.objects.create(
        owner=owner, patient=pet, starts_at=timezone.now(),
        status=Appointment.Status.CONFIRMED, assigned_vet=admin_user,
    )
    resp = auth_client.post(reverse("appointments:start_exam", args=[appt.pk]))
    assert resp.status_code == 302
    appt.refresh_from_db()
    assert appt.status == Appointment.Status.IN_EXAM
    exam = Examination.objects.get(appointment=appt)
    assert f"/muayeneler/{exam.pk}/" in resp.url
    # ikinci kez → yeni muayene oluşmamalı
    auth_client.post(reverse("appointments:start_exam", args=[appt.pk]))
    assert Examination.objects.filter(appointment=appt).count() == 1


def test_appointment_source_default_scheduled(db, admin_user):
    from apps.appointments.models import Appointment
    owner = Owner.objects.create(first_name="K", last_name="L", phone="0560")
    sp = Species.objects.create(name="Kuş")
    pet = Patient.objects.create(owner=owner, name="Cik", species=sp)
    appt = Appointment.objects.create(owner=owner, patient=pet, starts_at=timezone.now())
    assert appt.source == Appointment.Source.SCHEDULED
