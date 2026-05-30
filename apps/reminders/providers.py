"""
Mesaj sağlayıcı soyutlaması.

MVP: `ManualWaMeProvider` — gerçek otomatik gönderim yapmaz; sadece `wa.me` linki üretir.
Personel linke tıklayıp mesajı elle gönderir, sonra "Gönderildi" işaretler.
İleride `CloudApiProvider` aynı arayüzle eklenir; çağıran katman değişmez.
"""

from __future__ import annotations

from urllib.parse import quote


def normalize_phone(phone: str) -> str:
    """Türkiye numarasını wa.me için 90XXXXXXXXXX biçimine yaklaştırır."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits.startswith("0"):
        digits = "90" + digits[1:]
    elif digits.startswith("90"):
        pass
    elif len(digits) == 10:
        digits = "90" + digits
    return digits


class BaseMessageProvider:
    key = ""
    label = ""
    automatic = False

    def build_link(self, to_phone: str, body: str) -> str:
        return ""

    def send(self, message) -> bool:
        """OutboundMessage'ı gönderir. Manuel sağlayıcıda no-op (elle gönderilir)."""
        raise NotImplementedError


class ManualWaMeProvider(BaseMessageProvider):
    key = "manual_wame"
    label = "WhatsApp (manuel wa.me)"
    automatic = False

    def build_link(self, to_phone: str, body: str) -> str:
        return f"https://wa.me/{normalize_phone(to_phone)}?text={quote(body)}"

    def send(self, message) -> bool:
        # Manuel: gerçek gönderim yok. Sadece linkin hazır olduğundan emin ol.
        if not message.wa_link:
            message.wa_link = self.build_link(message.to_phone, message.body)
        return False  # otomatik gönderilmedi


def get_provider() -> BaseMessageProvider:
    # İleride settings/ClinicSettings'ten seçilebilir hale gelir.
    return ManualWaMeProvider()
