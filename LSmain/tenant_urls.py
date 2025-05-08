from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from LSCliente import views

# URLs específicas para tenants de cliente
urlpatterns = [
    path('admin/', admin.site.urls),
    # Redirecionar a raiz para a view clientehome
    path('', views.ClienteHomeView.as_view(), name='root'),
    # Adicione uma rota específica para /home/
    path('home/', views.ClienteHomeView.as_view(), name='clientehome'),
    # Incluir o resto das URLs do LSCliente com o namespace
    path('', include(('LSCliente.urls', 'LSCliente'), namespace='LSCliente')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)