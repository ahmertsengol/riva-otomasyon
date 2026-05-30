# Riva Otomasyon — geliştirme kısayolları (lokal, Docker'sız)
# WeasyPrint'in native kütüphaneleri (pango vb.) Homebrew'dan gelir.
export DYLD_FALLBACK_LIBRARY_PATH := /opt/homebrew/lib

PY := .venv/bin/python
TW := ./tailwindcss

.PHONY: help install css css-watch run migrate makemigrations seed reset-demo superuser test lint reminders

help:
	@echo "make install    - bağımlılıkları kur (venv)"
	@echo "make css        - Tailwind CSS derle (tek sefer)"
	@echo "make css-watch  - Tailwind CSS izle (geliştirme)"
	@echo "make run        - geliştirme sunucusu (runserver)"
	@echo "make migrate    - migrasyonları uygula"
	@echo "make seed       - örnek veriyi yükle"
	@echo "make reset-demo - veriyi sıfırla + yeniden yükle"
	@echo "make superuser  - yönetici kullanıcı oluştur"
	@echo "make test       - pytest"
	@echo "make lint       - ruff"
	@echo "make reminders  - hatırlatmaları üret (generate_reminders)"

install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

css:
	$(TW) -i static/css/input.css -o static/css/tailwind.out.css --minify

css-watch:
	$(TW) -i static/css/input.css -o static/css/tailwind.out.css --watch

run:
	$(PY) manage.py runserver

makemigrations:
	$(PY) manage.py makemigrations

migrate:
	$(PY) manage.py migrate

seed:
	$(PY) manage.py seed_demo

reset-demo:
	$(PY) manage.py seed_demo --reset

superuser:
	$(PY) manage.py createsuperuser

test:
	$(PY) -m pytest

lint:
	.venv/bin/ruff check .

reminders:
	$(PY) manage.py generate_reminders
