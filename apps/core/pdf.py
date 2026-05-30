"""
Ortak PDF üretim yardımcısı (WeasyPrint).

HTML şablonu render edip PDF döner. Tüm modüller (reçete, aşı kartı, aşı geçmişi)
bunu kullanır; WeasyPrint import'u fonksiyon içinde tutulur (native kütüphane
gerektirir; sadece PDF üretiminde yüklenir).

Not: macOS'te DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib gerekir (Makefile ayarlar).
"""

from __future__ import annotations

from django.http import HttpResponse
from django.template.loader import render_to_string


def render_pdf_response(template: str, context: dict, request, filename: str) -> HttpResponse:
    html = render_to_string(template, context, request=request)
    from weasyprint import HTML

    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
