"""Panel (dashboard) ve global arama."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import dashboard_context, global_search


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html", dashboard_context())


@login_required
def search(request):
    query = (request.GET.get("q") or "").strip()
    results = global_search(query) if query else None
    return render(request, "core/search.html", {"query": query, "results": results})
