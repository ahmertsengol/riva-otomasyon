# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Klinik **içi** kullanılan veteriner kliniği operasyon otomasyonu (Riva Veteriner, Marmaris).
Müşteri/pet sahibi paneli YOK — kullanıcı klinik personeli. **Arayüz Türkçe**; sahibe giden mesaj
şablonları TR/EN. Django 5.1 + PostgreSQL + HTMX/Alpine + Tailwind v4 + WeasyPrint (PDF).

Detaylı ürün/teknik plan ve milestone sırası: `/Users/ahmert/.claude/plans/frolicking-tinkering-spindle.md`.
Bu plan ile birlikte okunmalı — mimari kararların gerekçeleri oradadır.

## Commands

`make help` tüm kısayolları listeler. Hepsi `.venv/bin/python` ve `./tailwindcss` kullanır; Makefile
WeasyPrint için `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`'i otomatik ayarlar.

```bash
make migrate          # makemigrations DEĞİL — sadece migrate
make seed             # seed_demo: admin/admin123 + örnek veri
make reset-demo       # seed_demo --reset
make run              # runserver → http://127.0.0.1:8000
make css-watch        # Tailwind izleme (geliştirme sırasında ayrı terminal)
make css              # Tailwind tek seferlik --minify build
make test             # pytest
make lint             # ruff check
make reminders        # manage.py generate_reminders

# Tek test:
.venv/bin/python -m pytest tests/test_smoke.py::test_owner_list_and_create
# manage.py'yi elle çağırırken (PDF üretiyorsa):
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python manage.py <cmd>
```

Lokal Postgres rolü/DB: `riva` / `riva` / db `riva` (zaten oluşturuldu). `.env` ile bağlanır.
**Docker/Redis/Celery lokalde KURULMAZ** — sadece prod (`docs/DEPLOYMENT.md`).

## Settings & app layout

- `riva/settings/` paketi: `base.py` + `dev.py` + `prod.py`, `.env` (django-environ).
  `manage.py` → `riva.settings.dev`; `wsgi/asgi` → `riva.settings.prod`. pytest → `dev`.
- Tüm app'ler `apps/` altında; her `AppConfig.name = "apps.<app>"`. Yeni app eklerken `startapp apps/<x>`
  sonrası bu `name`'i düzelt ve `base.py:LOCAL_APPS`'e ekle. **`apps.accounts` ilk sırada** (custom User).
- `AUTH_USER_MODEL = "accounts.User"`.

## Mimari konvansiyonlar (kritik — uy)

**Otomatik denetim (audit).** İş modelleri `apps.core.models.BaseModel`'den türer. `BaseModel.save/delete`,
aktif kullanıcıyı `created_by`/`updated_by`'a yazar ve `AuditLog` üretir. Aktif kullanıcı/IP,
`apps.core.middleware.AuditContextMiddleware` → `apps.core.audit` thread-local'inden gelir. Yeni iş
modellerini **mutlaka `BaseModel`'den türet** (sadece zaman damgası için `TimeStampedModel`). Logu kapatmak
için `audit = False`. Aktör yoksa (seed, public API) alanlar null kalır — beklenen davranış.

**Formlar.** `apps.core.forms.StyledFormMixin` ilk taban olarak kullanılır (widget tipine göre otomatik
Tailwind sınıfı). Şablonda alanlar `{% include "partials/_field.html" with field=form.x %}` ile render edilir
(checkbox dahil otomatik).

**Tasarım sistemi.** Bileşen sınıfları `static/css/input.css` (`@layer components`): `.btn/.btn-primary/...`,
`.card/.card-pad`, `.table`, `.badge-{success,warning,danger,info,brand,neutral}`, `.nav-link`, `.input/.label`,
`.page-title/.section-title`. Açık tema + `brand` (teal) + anlamlı durum renkleri. İkonlar:
`{% include "partials/_icon.html" with name="..." %}` (isimler dosyada — yeni ikon eklemeden önce bak).
**Şablona Tailwind sınıfı eklediğinde CSS'i yeniden derle** (`make css` / `css-watch`), yoksa stil çıkmaz.

**Statik/JS.** `static/js/{htmx.min.js, alpine.min.js, fullcalendar.min.js}` lokalde vendor'lı. **CDN kullanma.**
HTMX CSRF, `base.html`'de body `hx-headers` ile gönderilir.

**URL'ler.** `riva/urls.py` app urls'lerini include eder; çoğu Türkçe slug (`sahipler/`, `hayvanlar/`,
`asilar/`, `hatirlatmalar/`, `kasa/`, `raporlar/`, `ayarlar/`). `appointments` ve `medical` kök `""` altında
include edilir, path'leri **kendi tam prefix'ini taşır** (`randevular/`, `muayeneler/` ...). `core.urls` en
sonda (`""` panel + `ara/` arama). Ayarlar `core/settings_urls.py` (`app_name="settings"`).
**Henüz var olmayan bir `{% url %}` adına ATIF YAPMA** — render anında patlar; modül gelene kadar sabit href kullan.

**Defansif panel/arama.** `apps/core/services.py` (`dashboard_context`, `global_search`) diğer modülleri
fonksiyon içinde lazy import eder + try/except ile sarar; böylece bir modül daha yazılmadan da panel/arama
çalışır. Yeni bir modül (ör. billing.Payment, vaccines.VaccineRecord) gelince ilgili `_safe(...)` bloğu
gerçek veriyle çalışmaya başlar — bu beklenen tasarım.

**Soyutlama katmanları.** OTP gönderimi `apps/core/otp.py` (`get_channel`; e-posta aktif, WhatsApp stub).
Hatırlatma gönderimi (M6) `BaseMessageProvider → ManualWaMeProvider` ile soyutlanacak — gerçek otomatik
WhatsApp gönderimi MVP'de YOK (manuel `wa.me`). Bu soyutlamaları koru; sağlayıcı eklerken üst katmanı değiştirme.

## Çalışma şekli (incremental, milestone bazlı)

Plan M0–M9 milestone'larına bölünmüş. **Tüm MVP milestone'ları (M0–M9) tamamlandı ve doğrulandı:**
randevu/takvim, tıbbi kayıtlar + reçete/aşı PDF, aşı protokol motoru, hatırlatma kuyruğu (manuel wa.me),
kasa (işlem/tahsilat/borç/e-fatura simülasyonu), raporlar, panel. Sonraki iş = MVP sonrası fazlar
(stok, gerçek e-fatura, POS, pet hotel, gelişmiş raporlar) ve prod dağıtımı (`docs/`).
Her milestone sonunda ZORUNLU doğrulama:
`makemigrations`+`migrate` → `manage.py check` → `ruff check . --fix` → tailwind build → `pytest` yeşil →
`runserver` ile en az bir gerçek HTTP akışı. **Doğrulanmamış kodu üst üste yığma.**

`seed_demo` (`apps/core/management/commands/seed_demo.py`) idempotent; yeni modeller eklendikçe burada örnek
veri de eklenmeli ki panel/takvim/listeler demoda dolu görünsün.

## Açık işler / sınırlar

- **Logo yok** → giriş/sidebar/PDF'te teal "R" yer tutucu; `ClinicSettings.logo` verilince değişir.
- **Aşı protokolü sabit kodlanmaz** — `VaccineDefinition` düzenlenebilir veri; seed'de uyarı notlu başlangıç şablonu.
- Prod (Docker/Caddy/Celery/deploy), backup ve landing page → otomasyon bağlama: `docs/` içinde NOT, şimdi yapılmaz.
