#!/bin/sh
# Konteyner başlangıcı: DB'yi bekle → migrate → örnek veri → sunucuyu başlat.
set -e

echo "PostgreSQL bekleniyor…"
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-riva}" >/dev/null 2>&1; do
  sleep 1
done
echo "PostgreSQL hazır."

python manage.py migrate --noinput
python manage.py seed_demo        # idempotent: tekrar çalıştırılabilir

echo "Uygulama başlıyor → http://localhost:8000  (giriş: admin / admin123)"
exec python manage.py runserver 0.0.0.0:8000
