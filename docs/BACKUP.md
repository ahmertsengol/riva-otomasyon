# Yedekleme / Geri Yükleme Notları (SONRAYA)

> İkinci sunucu / harici depo henüz yok. VPS alındığında düzenli yedek + **restore testi**
> kurulacak. Lokal demoda gerekli değildir.

## Neyi yedekliyoruz
1. **PostgreSQL** — tüm klinik verisi.
2. **`media/`** — yüklenen foto, lab PDF, operasyon görseli, aşı sertifikası vb.

## Günlük yedek (örnek)
```bash
# Veritabanı
pg_dump -Fc -U riva riva > /backups/riva_$(date +%F).dump
# Medya
tar czf /backups/media_$(date +%F).tar.gz media/
# 14 günden eskileri sil
find /backups -name 'riva_*.dump' -mtime +14 -delete
```
- cron veya Celery beat ile zamanla (ör. her gece 03:00).
- Mümkünse yedekleri **ikinci bir lokasyona** (harici disk / uzak sunucu / S3) kopyala.

## Geri yükleme
```bash
createdb -U postgres riva_restore
pg_restore -U postgres -d riva_restore /backups/riva_2026-01-01.dump
tar xzf /backups/media_2026-01-01.tar.gz
```
- **Restore testi**: ayda en az bir kez yedeği boş bir DB'ye geri yükleyip doğrula.
  Test edilmemiş yedek = yedek değildir.
