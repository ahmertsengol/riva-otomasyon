# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Klinik **içi** kullanılan veteriner kliniği operasyon otomasyonu (Riva Veteriner, Marmaris).
Müşteri/pet sahibi paneli YOK — kullanıcı klinik personeli (tek admin). **Arayüz Türkçe**; sahibe
giden mesaj şablonları TR/EN. Django 5.1 + PostgreSQL + HTMX/Alpine + Tailwind v4 + WeasyPrint (PDF).
Chrome'a "uygulama olarak" kurulabilen PWA.

Detaylı ürün/teknik plan: `/Users/ahmert/.claude/plans/frolicking-tinkering-spindle.md` (kararların gerekçeleri).

## Commands

`make help` tüm kısayolları listeler. Hepsi `.venv/bin/python` ve `./tailwindcss` kullanır; Makefile
WeasyPrint için `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`'i otomatik ayarlar.

```bash
make migrate / make makemigrations
make seed             # seed_demo: admin/admin123 + örnek veri (idempotent)
make reset-demo       # seed_demo --reset
make run              # runserver → http://127.0.0.1:8000
make css / css-watch  # Tailwind --minify build / izleme (ayrı terminal)
make test             # pytest
make lint             # ruff check
make reminders        # manage.py generate_reminders (hatırlatma kuyruğunu doldurur)

# Tek test:
.venv/bin/python -m pytest tests/test_smoke.py::test_owner_list_and_create
# PDF üreten manage.py komutlarını elle çağırırken DYLD ekle:
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python manage.py <cmd>
```

- **Lokal geliştirme = `runserver` + lokal Postgres** (Docker GEREKMEZ). Postgres rolü/DB: `riva`/`riva`/`riva`.
- **PDF testleri** WeasyPrint native kütüphanesi ister → `make test` DYLD'yi ayarlar; doğrudan `pytest`
  çağırırsan `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` ekle.
- Tailwind: derlenmiş CSS (`static/css/tailwind.out.css`) repoya **commit'lenir** (klinikte build yok);
  ~100MB `tailwindcss` binary'si gitignore'da.

## Deploy & otomatik güncelleme (kurulu ve çalışıyor)

Klinik PC'sinde **Docker Desktop + `docker compose up -d`** yeterli. Akış:
`git push` → **GitHub Actions** (`.github/workflows/docker-publish.yml`) imajı derleyip
`ghcr.io/ahmertsengol/riva-otomasyon:latest`'a yükler → klinikteki **Watchtower** (~60 sn) yeni imajı
çekip `web`'i yeniden başlatır. Migrasyonlar konteyner açılışında (`docker/entrypoint.sh`) **otomatik**
uygulanır; veriler korunur.

- `docker-compose.yml` = **klinik/ciddi kullanım** (GHCR imajı + `web`(gunicorn) + `db` + `scheduler` + **`backup`** + `watchtower`). Ayar: `riva.settings.clinic` (DEBUG=False).
- `docker-compose.build.yml` = kaynaktan derleme (dev/yedek/internetsiz; `SEED_DEMO=1`).
- `scheduler` servisi `manage.py run_scheduler` çalıştırır (saatlik `generate_reminders`; Celery'siz).
- `backup` servisi günlük `pg_dump` → `./backups` (14 günden eski silinir).
- GHCR paketi **public** olmalı (ayarlandı). Detay: `docs/DEMO_KURULUM.md`, `docs/DEPLOYMENT.md`.

**ÖNEMLİ — Watchtower yalnızca İMAJI günceller, compose dosyasını DEĞİL.** `docker-compose.yml`,
`entrypoint.sh`, ayar profili gibi şeyleri değiştirdiysen klinikte `git pull` (veya ZIP) + `docker compose up -d`
gerekir. Gerçek veriyle temiz başlangıç için bir kez `docker compose down -v`.

## Kurulum verisi: bootstrap vs seed_demo (KARIŞTIRMA)

- **`manage.py bootstrap`** = ÜRETİM güvenli, idempotent, SAHTE VERİ YOK: admin (şifre `ADMIN_PASSWORD`
  env), ClinicSettings+logo, türler, aşı protokolleri, mesaj şablonları, hatırlatma kuralları, hizmetler.
  Konteyner her açılışta çalışır (`entrypoint.sh`: migrate → collectstatic → bootstrap → gunicorn).
- **`manage.py seed_demo`** = yalnızca DEMO sahte verisi (sahip/hayvan/randevu/kasa). `bootstrap`'i çağırır,
  üstüne sahte veri ekler. Klinikte OTOMATİK ÇALIŞMAZ (sadece `SEED_DEMO=1` env ile). `--reset` sahte/işlem
  verisini siler, yapılandırmayı korur. Yeni model/veri eklerken: yapılandırma → bootstrap, sahte → seed_demo.

## Settings & app layout

- `riva/settings/`: `base.py` + `dev.py` + `prod.py`, `.env` (django-environ).
  `manage.py` → `riva.settings.dev`; `wsgi/asgi` → `prod`; pytest → `dev`. Docker da `dev` kullanır (DEBUG açık demo).
- Tüm app'ler `apps/` altında; her `AppConfig.name = "apps.<app>"`. Yeni app: `startapp apps/<x>` →
  `name`'i `apps.<x>` yap → `base.py:LOCAL_APPS`'e ekle. **`apps.accounts` ilk sırada** (custom User).
- `AUTH_USER_MODEL = "accounts.User"`. URL include'ları `riva/urls.py`'de; `core.urls` en sonda.

## Mimari konvansiyonlar (KRİTİK — uy)

**Otomatik denetim.** İş modelleri `apps.core.models.BaseModel`'den türer → `save/delete`'te aktif
kullanıcıyı `created_by/updated_by`'a yazar + `AuditLog` üretir (aktif kullanıcı/IP
`core.middleware.AuditContextMiddleware` → `core.audit` thread-local'inden). Yeni iş modellerini
**mutlaka `BaseModel`'den türet**. Log kapatmak: `audit = False` (ör. `ChargeLine`).

**Formlar.** `apps.core.forms.StyledFormMixin` ilk taban (widget tipine göre Tailwind sınıfı). Alanlar
`{% include "partials/_field.html" with field=form.x %}` ile render edilir (checkbox dahil).

**Bağımlı açılır liste (HTMX) — yaygın desen.** "A seçilince B listesi filtrelensin" için (owner→hayvan,
hayvan→tür-aşı-protokolü, hayvan→muayene). Dört parça:
1. **Endpoint** parent id alıp `_*_select.html` partial'ı (içinde `<select name=.. id=id_..>`) döner.
   Mevcutlar: `patients:options` (owner→patient), `vaccines:definition_options` (patient→species protokol),
   `medical:examination_options` (patient→examination).
2. **Form** parent alanın widget'ına `hx-get/hx-target="#<x>-field"/hx-trigger="change"/hx-swap="innerHTML"`
   ekler (`__init__`'te).
3. **Template** bağımlı alanı `_field.html` yerine `<div id="<x>-field">{% include partial %}</div>` + elle label.
4. **View** `get_context_data` başlangıç listesini (`init_patients`/`init_definitions`/`init_examinations`) verir.
   Hedef id'ler: `#patient-field`, `#vaccine-def-field`, `#examination-field`. (Kullanan formlar: reminders
   manual, billing charge, appointment, vaccines apply, medical prescription/lab.)

**Tasarım sistemi.** Bileşen sınıfları `static/css/input.css` (`@layer components`): `.btn*`, `.card*`,
`.table`, `.badge-*`, `.nav-link`, `.input/.label`, `.icon-btn`, `.notif-badge`, `.page-title`. Açık tema +
`brand` (teal) + durum renkleri. İkonlar: `{% include "partials/_icon.html" with name="..." %}`.
**Arbitrary değer (`h-[18px]`, `text-[11px]`) yerine ham CSS'li bileşen sınıfı kullan** — minify build'de
arbitrary'ler bazen düşer (notif-badge bu yüzden ham CSS). **Şablona sınıf ekleyince CSS'i yeniden derle**
(`make css`), sonra Docker'da `collectstatic` otomatik.

**Statik/JS.** `static/js/{htmx,alpine,fullcalendar}.min.js` vendor'lı (CDN kullanma). HTMX CSRF `base.html`'de
body `hx-headers` ile gönderilir.

**Defansif panel/arama.** `apps/core/services.py` (`dashboard_context`, `global_search`) ve
`core/context_processors.py` (zil sayacı `action_count`) diğer modülleri fonksiyon içinde lazy import +
try/except ile sarar; modül yoksa 0/boş döner. Yeni modül gelince kendiliğinden gerçek veriyle çalışır.

**Soyutlama katmanları (koru, üst katmanı değiştirme).**
- OTP: `apps/core/otp.py` `get_channel` (e-posta aktif, WhatsApp stub).
- Mesaj gönderimi: `apps/reminders/providers.py` `BaseMessageProvider → ManualWaMeProvider`
  (gerçek otomatik WhatsApp YOK; `wa.me` linki üretir, personel elle gönderir).

## Hatırlatma / Bildirim sistemi

- `reminders.services.generate_reminders()` aktif `ReminderRule`'lara göre yaklaşan randevu (sadece
  `Appointment.reminder_enabled=True`) ve yaklaşan/geciken aşıları tarayıp `OutboundMessage(pending)` üretir.
  **`dedupe_key` ile idempotent.** `manage.py generate_reminders` veya `run_scheduler` ile periyodik çalışır.
- Hiçbir şey otomatik gönderilmez — kuyruktan admin `wa.me` ile gönderip "Gönderildi" işaretler.
- Üst bar zili (`_topbar.html`): `action_count = due_reminder_count + pending_request_count`
  (context processor, her sayfa yüklemesinde hesaplanır; canlı değil).

## Aşı protokol motoru

`VaccineDefinition` düzenlenebilir veridir (sabit kod YOK). Çok-doz **birincil seri** (`series_doses`,
`series_interval_days`) + sonrası **rapel** (`repeat_interval_days`). `VaccineRecord.save` kaçıncı dozda
olduğunu sayıp `next_due_at`'i hesaplar. Aşı uygulamada (`create_followup` açıksa) sonraki doz için
**"planlandı" randevu otomatik** oluşur (Karma 1 → Karma 2).

## Performans / tuzaklar

- `Owner.balance` **property** N+1'dir; liste/sorgu görünümlerinde kullanma. `OwnerListView` bunun yerine
  Subquery ile `balance_amount` annotate eder (template `owner.balance_amount` kullanır). Annotation adı
  property'den **farklı** olmalı (property data-descriptor olduğu için aynı adı gölgeler).
- `{% url %}`'i **var olmayan** bir route adına çağırma (render anında patlar). Yeni modül gelene kadar sabit href.
- PWA: `manifest.webmanifest` ve `sw.js` **kökten** `core.views` ile servis edilir (SW kapsamı + mime tipi için);
  SW network-first (oto-güncelleme ile stale çakışması olmasın).

## Commits

Commit mesajlarında **Claude imzası / `Co-Authored-By` KULLANMA** (kullanıcı tercihi). `-c commit.gpgsign=false`
ile imzasız commit'le. Push, klinikte otomatik dağıtımı tetikler — push'tan önce kullanıcıya sor.

## Doğrulama (her değişiklikten sonra ZORUNLU)

`makemigrations`+`migrate` → `manage.py check` → `ruff check . --fix` → `make css` → `pytest` yeşil →
mümkünse gerçek HTTP akışı (test client veya runserver). `seed_demo` idempotent; yeni modeller eklendikçe
örnek veri de eklenmeli ki demo dolu görünsün. **Doğrulanmamış kodu üst üste yığma.**

## Durum

MVP (M0–M9) tamam: sahip/hayvan, randevu+takvim, tıbbi kayıtlar + reçete/aşı/aşı-geçmişi PDF, aşı protokol
motoru + seri, hatırlatma kuyruğu + zamanlayıcı + bildirim zili, kasa (işlem/tahsilat/borç/e-fatura
simülasyonu), raporlar, panel, PWA, oto-deploy. Logo entegre. **Sonraki:** MVP sonrası fazlar (stok, gerçek
e-fatura, POS, pet hotel, gelişmiş raporlar) — `docs/`.
