# Riva Otomasyon — demo/prod imajı
# WeasyPrint (PDF) için gereken native kütüphaneler imaja gömülür; klinik PC'sinde
# ayrıca pango/GTK kurulumu GEREKMEZ.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=riva.settings.dev

# WeasyPrint sistem bağımlılıkları + postgres client (healthcheck/debug için)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
