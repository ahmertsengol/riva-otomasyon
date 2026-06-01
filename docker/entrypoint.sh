#!/bin/sh
# Konteyner başlangıcı: DB'yi bekle → migrate → statikleri topla → bootstrap → gunicorn.
# Üretim/ciddi kullanım: SAHTE veri YÜKLENMEZ (sadece bootstrap: admin + yapılandırma).
# Demo verisi istenirse elle: docker compose exec web python manage.py seed_demo
set -e

echo "PostgreSQL bekleniyor…"
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-riva}" >/dev/null 2>&1; do
  sleep 1
done
echo "PostgreSQL hazır."

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py bootstrap        # idempotent: admin + klinik + protokoller + şablonlar

# İsteğe bağlı: SEED_DEMO=1 ise sahte demo verisi de yükle
if [ "${SEED_DEMO:-0}" = "1" ]; then
  python manage.py seed_demo
fi

echo "Uygulama başlıyor (gunicorn) → :8000"
exec gunicorn riva.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-3}" --timeout 60
