# Production / VPS Dağıtım Notları (SONRAYA)

> Bu doküman **prod hazırlık** içindir. Lokal demo bunların hiçbirini gerektirmez.
> VPS alındığında uygulanacak; veri modeli ve ayarlar şimdiden buna uyumlu yazılmıştır.

## Hedef topoloji (tek VPS, Docker Compose)
- `web` — Gunicorn + Django (`riva.settings.prod`)
- `db` — PostgreSQL 16 (kalıcı volume)
- `redis` — Celery broker/result
- `celery-worker` — hatırlatma gönderimi, ağır işler
- `celery-beat` — `generate_reminders` vb. zamanlanmış görevler
- `caddy` — reverse proxy + otomatik TLS (Let's Encrypt). Alternatif: Nginx + certbot.

## Yapılacaklar (özet)
1. `Dockerfile` (python:3.12-slim + pango/weasyprint sistem bağımlılıkları) ve
   `docker-compose.yml` (yukarıdaki servisler) yaz.
2. `prod.py` zaten hazır: `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, HTTPS güvenlik
   başlıkları, SMTP, `REDIS_URL`. Tüm sırlar ortam değişkeni / Docker secret.
3. Statikler: `collectstatic` + WhiteNoise (Caddy'den de servis edilebilir).
4. `media/` için kalıcı volume; ileride MinIO/S3'e geçiş `STORAGES` ile.
5. Celery: `generate_reminders`'ı beat ile zamanla (ör. her 15 dk / her sabah 08:00).

## GitHub push → otomatik deploy
- GitHub Actions workflow: `main`'e push → SSH ile VPS'e bağlan → `git pull` →
  `docker compose build && docker compose up -d` → `migrate` → `collectstatic`.
- Alternatif: webhook + sunucuda watchtower / basit deploy scripti.
- **Geliştirme sırasında** her commit'te build gerekmez; bu akış yalnızca prod içindir.

## Açılış kontrol listesi
- [ ] `DEBUG=False`, güçlü `SECRET_KEY`, doğru `ALLOWED_HOSTS`
- [ ] HTTPS zorunlu (Caddy otomatik TLS)
- [ ] DB ve media yedeği (bkz. `BACKUP.md`)
- [ ] Rate limit (login/OTP), güvenlik başlıkları
- [ ] Gmail SMTP uygulama şifresi (`EMAIL_HOST_PASSWORD`)
