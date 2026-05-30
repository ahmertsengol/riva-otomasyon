# Riva Veteriner — Klinik Otomasyon Sistemi

Klinik **içi** kullanılacak, web tabanlı operasyon otomasyonu (sahip/hayvan kaydı, randevu,
aşı takibi, muayene, reçete, basit kasa, hatırlatma kuyruğu). MVP lokal geliştirme içindir;
prod (VPS + Docker) notları `docs/` altındadır.

- **Stack:** Django 5 · PostgreSQL · HTMX + Alpine + Tailwind v4 · WeasyPrint (PDF)
- **Arayüz:** Türkçe, açık tema + tıbbi teal vurgu, desktop öncelikli (raporlar/kasa mobil-uyumlu)
- **Tasarım kararları:** `../../.claude/plans/frolicking-tinkering-spindle.md` ve `docs/`

## 🚀 Hızlı Demo (klinik PC'si — Windows + Docker)
Sadece Docker Desktop kurun, sonra proje klasöründe:
```bash
docker compose up -d          # GHCR'daki hazır imajı çeker + oto-güncelleyici (Watchtower)
```
→ http://localhost:8000 · giriş **admin / admin123**.
Her `git push` sonrası uygulama klinik PC'sinde **otomatik güncellenir** (GitHub Actions → GHCR → Watchtower).
Kaynaktan derlemek için: `docker compose -f docker-compose.build.yml up -d --build`.
Adım adım: **`docs/DEMO_KURULUM.md`**.

## Gereksinimler (lokal)
- Python 3.11+
- PostgreSQL 14+ (lokalde çalışır durumda, port 5432)
- Homebrew `pango` (WeasyPrint için): `brew install pango`
- (Tailwind CLI binary `./tailwindcss` repoda indirilir; Node gerekmez)

## Kurulum

```bash
# 1) Sanal ortam + bağımlılıklar
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 2) PostgreSQL rolü + veritabanı (postgres süper kullanıcı şifresi sorulur)
/Library/PostgreSQL/17/bin/psql -U postgres -h localhost \
  -c "CREATE ROLE riva WITH LOGIN PASSWORD 'riva' CREATEDB;" \
  -c "CREATE DATABASE riva OWNER riva;"

# 3) Ortam dosyası
cp .env.example .env   # (repoda hazır .env de var)

# 4) Migrasyon + örnek veri
make migrate
make seed              # admin / admin123 ve gerçekçi demo verisi

# 5) Çalıştır (iki terminal)
make css-watch         # Terminal 1: Tailwind izleme
make run               # Terminal 2: http://127.0.0.1:8000
```

> **WeasyPrint / PDF:** `make` hedefleri `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`
> ortam değişkenini otomatik ayarlar. `manage.py`'yi elle çalıştırıyorsanız PDF üretimi
> için bu değişkeni siz ekleyin.

## Sık kullanılan komutlar
`make help` — tüm kısayollar. (run, css, migrate, seed, reset-demo, superuser, test, lint, reminders)

## Proje yapısı
- `riva/settings/` — base / dev / prod ayrımı (`.env` ile)
- `apps/` — modüler app'ler (core, accounts, owners, patients, appointments, medical,
  vaccines, reminders, billing, files, reports)
- `templates/`, `static/` — arayüz + tasarım sistemi (`static/css/input.css`)
- `docs/` — deployment, backup, landing page entegrasyonu (prod'a hazırlık notları)
