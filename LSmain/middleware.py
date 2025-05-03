from django_tenants.middleware import TenantMainMiddleware
from LSDash.models import Dominio, ConfiguracaoSistema, SessaoUsuario
from django.utils import timezone
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
import logging
from django.http import HttpResponseNotFound
from django_tenants.utils import get_tenant_model, get_public_schema_name
from django.db import connections


logger = logging.getLogger(__name__)


class SessionTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Processar a requisição antes da view
        if request.user.is_authenticated:
            # Verificar inatividade
            
            # Obter configurações
            configuracao = ConfiguracaoSistema.obter_configuracao()
            tempo_maximo = configuracao.tempo_maximo_inatividade
            
            # Verificar última atividade
            ultima_atividade = request.session.get('ultima_atividade')
            agora = timezone.now()
            
            if ultima_atividade:
                ultima_atividade = timezone.datetime.fromisoformat(ultima_atividade)
                if (agora - ultima_atividade).total_seconds() > (tempo_maximo * 60):
                    # Tempo de inatividade excedido
                    logout(request)
                    messages.warning(request, "Sua sessão expirou devido à inatividade.")
                    return redirect(reverse('login'))
            
            # Atualizar última atividade
            request.session['ultima_atividade'] = agora.isoformat()
            
            # Rastrear a sessão
            if hasattr(request, 'session') and request.session.session_key:
                SessaoUsuario.objects.update_or_create(
                    usuario=request.user,
                    chave_sessao=request.session.session_key,
                    defaults={
                        'ultima_atividade': timezone.now(),
                        'endereco_ip': self.get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')
                    }
                )
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip