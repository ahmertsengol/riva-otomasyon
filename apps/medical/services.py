"""Hasta zaman çizelgesi için tıbbi ve operasyonel kayıtları birleştirir."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from django.urls import reverse
from django.utils import timezone


@dataclass
class TimelineEvent:
    date: datetime
    label: str
    title: str
    detail: str = ""
    tone: str = "brand"
    url: str = ""


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    dt = datetime.combine(value, time.min)
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


def patient_timeline(patient) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []

    try:
        appointments = patient.appointments.select_related("assigned_vet").all()
        for appt in appointments:
            tone = {
                "completed": "success",
                "cancelled": "danger",
                "no_show": "warning",
                "requested": "info",
            }.get(appt.status, "brand")
            vet = f" · {appt.assigned_vet.display_name}" if appt.assigned_vet_id else ""
            events.append(
                TimelineEvent(
                    date=appt.starts_at,
                    label="Randevu",
                    title=f"{appt.get_type_display()} · {appt.get_status_display()}",
                    detail=f"{appt.duration_min} dk{vet}",
                    tone=tone,
                    url=reverse("appointments:detail", args=[appt.pk]),
                )
            )
    except Exception:
        pass

    for exam in patient.examinations.select_related("vet").all():
        detail_parts = []
        if exam.diagnosis:
            detail_parts.append(exam.diagnosis)
        if exam.vet_id:
            detail_parts.append(exam.vet.display_name)
        events.append(
            TimelineEvent(
                date=exam.created_at,
                label="Muayene",
                title=exam.complaint or "Muayene kaydı",
                detail=" · ".join(detail_parts),
                tone="success",
                url=reverse("medical:examination_detail", args=[exam.pk]),
            )
        )

    for prescription in patient.prescriptions.select_related("vet").prefetch_related("items").all():
        item_names = ", ".join(item.drug_name for item in prescription.items.all()[:3])
        events.append(
            TimelineEvent(
                date=prescription.created_at,
                label="Reçete",
                title=item_names or "Reçete",
                detail=prescription.vet.display_name if prescription.vet_id else "",
                tone="info",
                url=reverse("medical:prescription_detail", args=[prescription.pk]),
            )
        )

    for operation in patient.operations.select_related("vet").all():
        events.append(
            TimelineEvent(
                date=operation.date,
                label="Operasyon",
                title=operation.type,
                detail=operation.result,
                tone="warning",
                url=reverse("medical:operation_detail", args=[operation.pk]),
            )
        )

    try:
        vaccine_records = patient.vaccine_records.select_related("vaccine_definition", "vet").all()
        for record in vaccine_records:
            detail_parts = []
            if record.next_due_at:
                detail_parts.append(f"Sonraki: {record.next_due_at:%d.%m.%Y}")
            if record.vet_id:
                detail_parts.append(record.vet.display_name)
            events.append(
                TimelineEvent(
                    date=_as_datetime(record.applied_at),
                    label="Aşı",
                    title=record.display_name,
                    detail=" · ".join(detail_parts),
                    tone="warning" if record.is_upcoming else "success",
                    url=reverse("vaccines:record_detail", args=[record.pk]),
                )
            )
    except Exception:
        pass

    for lab in patient.lab_results.all():
        events.append(
            TimelineEvent(
                date=_as_datetime(lab.date),
                label="Lab",
                title=lab.test_name,
                detail=lab.result_note,
                tone="info",
                url=reverse("medical:lab_result_detail", args=[lab.pk]),
            )
        )

    for note in patient.medical_notes.all():
        events.append(
            TimelineEvent(
                date=note.created_at,
                label="Not",
                title=note.body,
                tone="neutral",
                url=reverse("medical:note_detail", args=[note.pk]),
            )
        )

    return sorted(events, key=lambda event: event.date, reverse=True)
