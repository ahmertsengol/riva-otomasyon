"""Ayarlar bölümü — klinik bilgisi, tür yönetimi, denetim kaydı."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ClinicSettingsForm
from .models import AuditLog, ClinicSettings


@login_required
def settings_index(request):
    clinic = ClinicSettings.load()
    if request.method == "POST":
        form = ClinicSettingsForm(request.POST, request.FILES, instance=clinic)
        if form.is_valid():
            form.save()
            messages.success(request, "Klinik ayarları güncellendi.")
            return redirect("settings:index")
    else:
        form = ClinicSettingsForm(instance=clinic)
    return render(request, "settings/index.html", {"form": form})


@login_required
def species_manage(request):
    from apps.patients.forms import SpeciesForm
    from apps.patients.models import Species

    if request.method == "POST":
        form = SpeciesForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tür eklendi.")
            return redirect("settings:species")
    else:
        form = SpeciesForm()
    species = Species.objects.all()
    return render(request, "settings/species.html", {"species": species, "form": form})


@login_required
def species_toggle(request, pk):
    from apps.patients.models import Species

    sp = get_object_or_404(Species, pk=pk)
    sp.active = not sp.active
    sp.save(update_fields=["active", "updated_at"])
    return redirect("settings:species")


@login_required
def audit_log(request):
    logs = AuditLog.objects.select_related("actor")[:200]
    return render(request, "settings/audit_log.html", {"logs": logs})
