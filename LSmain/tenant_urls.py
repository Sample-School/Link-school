from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # URLs específicas para os tenants
    path('', include('LSCliente.urls')),  # Certifique-se que LSCliente tem um urls.py
    
    # Se você quiser compartilhar algumas URLs com o público,
    # você pode incluí-las aqui também
    # path('shared/', include('shared_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)