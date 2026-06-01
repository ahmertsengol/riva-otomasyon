"""Panel (dashboard), global arama ve PWA (manifest + service worker)."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static

from .services import dashboard_context, global_search


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html", dashboard_context())


@login_required
def search(request):
    query = (request.GET.get("q") or "").strip()
    results = global_search(query) if query else None
    return render(request, "core/search.html", {"query": query, "results": results})


# --- PWA (Chrome app olarak yüklenebilirlik) ---
def manifest(request):
    data = {
        "name": "Riva Veteriner Otomasyon",
        "short_name": "Riva Vet",
        "description": "Klinik içi operasyon otomasyonu",
        "lang": "tr",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#0d9488",
        "icons": [
            {"src": static("img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("img/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("img/icon-maskable-512.png"), "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")


# Service Worker — kökten servis edilir ki tüm siteyi kapsasın.
# Network-first (her zaman güncel; çevrimdışıysa önbellekten) — oto-güncelleme ile çakışmaz.
_SW_JS = """
const CACHE = 'riva-cache-v1';
self.addEventListener('install', (e) => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  e.respondWith(
    fetch(req).then((res) => {
      if (req.url.includes('/static/')) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match(req))
  );
});
"""


def service_worker(request):
    return HttpResponse(_SW_JS, content_type="application/javascript")
