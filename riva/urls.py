"""Riva Veteriner Otomasyon — kök URL yapılandırması."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
    # İş modülleri (milestone'lar geliştikçe açılır):
    path("sahipler/", include("apps.owners.urls")),
    path("hayvanlar/", include("apps.patients.urls")),
    path("", include("apps.appointments.urls")),
    path("", include("apps.medical.urls")),
    path("asilar/", include("apps.vaccines.urls")),
    path("hatirlatmalar/", include("apps.reminders.urls")),
    path("kasa/", include("apps.billing.urls")),
    path("raporlar/", include("apps.reports.urls")),
    path("ayarlar/", include("apps.core.settings_urls")),
    # Panel + arama kök seviyede (en sonda; "" path'i yakalar):
    path("", include("apps.core.urls")),
]

# Yüklenen dosyalar (logo, foto): DEBUG'da static() ile, üretimde de servis edilsin
# (klinik içi düşük trafik; statikler WhiteNoise, media bu route ile).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
