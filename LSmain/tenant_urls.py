from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from LSCliente import views

# URLs específicas para tenants de cliente
urlpatterns = [
    path('admin/', admin.site.urls),
    # Rota raiz redireciona para home do cliente
    path('', views.ClienteHomeView.as_view(), name='root'),
    # Home específica do cliente
    path('home/', views.ClienteHomeView.as_view(), name='clientehome'),
    # Todas as URLs do LSCliente com namespace
    path('', include(('LSCliente.urls', 'LSCliente'), namespace='LSCliente')),
]

# Servir arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)