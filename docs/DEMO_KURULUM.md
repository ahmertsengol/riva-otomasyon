# Demo Kurulumu — Windows + Docker (klinik PC'si)

Bu yöntemle klinik bilgisayarına **yalnızca Docker Desktop** kurulur; Python, PostgreSQL,
PDF kütüphaneleri vb. **elle kurulmaz** — hepsi otomatik gelir.

## 1) Docker Desktop kur (tek seferlik)
1. https://www.docker.com/products/docker-desktop/ → **Download for Windows**
2. İndirilen kurulumu çalıştır, varsayılan ayarlarla kur (WSL2 gerekirse kurulum kendisi halleder).
3. Bilgisayarı yeniden başlat, **Docker Desktop**'ı aç ve sağ alttaki simge **yeşil/çalışıyor** olsun.

## 2) Projeyi indir
**Kolay yol (Git gerekmez):**
1. GitHub repo sayfasında yeşil **Code** → **Download ZIP**.
2. ZIP'i bir klasöre çıkar (ör. `C:\riva-otomasyon`).

**Veya Git ile (güncelleme kolay olur):**
```powershell
git clone https://github.com/ahmertsengol/riva-otomasyon.git
cd riva-otomasyon
```

## 3) Çalıştır
Proje klasöründe **PowerShell** aç (klasörde boş alana Shift+Sağ tık → "PowerShell penceresi aç")
ve şunu yaz:
```powershell
docker compose up -d
```
- GitHub'da yayınlanan **hazır imaj** indirilir (klinik PC'sinde derleme yapılmaz).
- Otomatik olarak: veritabanı kurulur, tablolar oluşturulur, **örnek veri** yüklenir.
- Ayrıca **Watchtower** adlı bir oto-güncelleyici başlar (aşağıya bakın).

> İnternet yoksa veya imaj henüz yayınlanmadıysa, kaynaktan derleyerek de çalıştırabilirsin:
> `docker compose -f docker-compose.build.yml up -d --build`

## 4) Aç ve giriş yap
Tarayıcıdan: **http://localhost:8000**
Giriş: **admin / admin123**

## 🔄 Otomatik güncelleme (her push'ta)
Sistem "kendini güncelleyen uygulama" gibi çalışır:

1. Geliştirici `git push` yapar →
2. **GitHub Actions** yeni Docker imajını otomatik derleyip `ghcr.io`'ya yükler →
3. Klinik PC'sindeki **Watchtower** (her ~60 sn'de bir kontrol eder) yeni imajı görür,
   indirir ve uygulamayı **otomatik yeniden başlatır**. Klinikte hiçbir şey yapman gerekmez.

Güncelleme yaklaşık **1–2 dakika** içinde klinik PC'sine yansır. Verilerin (hasta, randevu…)
korunur; sadece uygulama kodu yenilenir.

> **Tek seferlik gereklilik:** GHCR imaj paketinin "public" olması gerekir (yoksa klinik PC'si
> indiremez). İlk push'tan sonra GitHub'da repo → **Packages → riva-otomasyon → Package settings
> → Change visibility → Public** yapılır. (Geliştirici bir kez yapar.)

## Günlük kullanım
| İşlem | Komut |
|---|---|
| Başlat | `docker compose up -d` |
| Durdur | `docker compose down` |
| Yeniden başlat | `docker compose restart` |
| Günlük/şifre kodu vb. logları gör | `docker compose logs -f web` |
| Güncelle | **Otomatik** (Watchtower) — elle bir şey yapmana gerek yok |
| Hemen güncelle (beklemeden) | `docker compose pull web && docker compose up -d` |

> **Şifre sıfırlama kodu (OTP):** Demo'da e-posta gerçekten gönderilmez; kod konteyner
> loglarına yazılır → `docker compose logs web` ile görebilirsin.

## Veriler nerede?
- Veritabanı ve yüklenen dosyalar (logo, fotoğraflar) Docker **volume**'larında kalıcıdır;
  `docker compose down` veriyi silmez. Tamamen sıfırlamak istersen: `docker compose down -v`.

## Önemli notlar
- Bu kurulum **demo/iç ağ** içindir (DEBUG açık, basit şifre). Gerçek internete açık
  sunucu (VPS) kurulumu için `docs/DEPLOYMENT.md`'ye bakın; orada HTTPS, güçlü şifreler,
  yedekleme ve otomatik deploy anlatılır.
- Klinik logosu repoda hazır gelir ve giriş ekranı, menü ve PDF'lerde görünür.
