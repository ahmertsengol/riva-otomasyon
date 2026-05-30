# Landing Page → Otomasyon Entegrasyonu (SONRAYA)

Mevcut landing page (`~/Developer/vet-web`, Next.js, Vercel) randevu formu şu an yalnızca
**WhatsApp linki** üretiyor (`src/components/AppointmentForm.tsx`). Otomasyon canlıya
(VPS) alındığında, form aynı anda otomasyona da **randevu talebi** düşürebilir.

## Otomasyon tarafı (HAZIR olacak)
`POST /api/appointment-requests/` — JSON, kimlik doğrulama gerektirmez (public), CSRF-muaf,
basit rate-limit. Gövde alanları landing formuyla birebir uyumludur:

```json
{
  "name": "Ad Soyad",
  "phone": "05xx...",
  "pet_name": "Boncuk",
  "pet_species": "Kedi",
  "requested_at": "2026-02-01 14:00",
  "subject": "Aşı",
  "message": "..."
}
```
Kayıt → "Randevu Talepleri" ekranına `source=web` olarak düşer, panelde rozet gösterilir.

## Landing tarafı (deploy sonrası yapılacak DEĞİŞİKLİK)
`AppointmentForm.tsx` içindeki `handleWhatsApp` korunur; ek olarak forma submit'te
otomasyon endpoint'ine `fetch` ile POST eklenir:

```ts
await fetch("https://otomasyon.rivaveteriner.com/api/appointment-requests/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    name: form.name, phone: form.phone, pet_name: "",
    pet_species: form.petType, requested_at: form.date,
    subject: form.subject, message: form.message,
  }),
}).catch(() => {});   // hata olsa da WhatsApp akışı bozulmaz
```

## Dikkat
- CORS: otomasyon endpoint'i landing origin'ine izin vermeli (prod ayarında).
- Spam: rate-limit + basit honeypot/recaptcha (ileride) düşünülmeli.
- MVP'de bu bağlantı **kurulmaz**; endpoint hazır bırakılır, landing deploy sonrası güncellenir.
