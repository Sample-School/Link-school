from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('LSDash.urls')),  # URLs do app principal
]

if settings.DEBUG:
    urlpatterns += [
        path('', include('LSCliente.urls')),  # URLs de cliente em desenvolvimento
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)