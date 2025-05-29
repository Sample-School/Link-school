from django_tenants.middleware import TenantMainMiddleware
from LSDash.models import Dominio, ConfiguracaoSistema, SessaoUsuario
from LSCliente.models import ClienteSystemSettings
from django.utils import timezone
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
import logging
from django.http import HttpResponseNotFound
from django_tenants.utils import get_tenant_model, get_public_schema_name
from django.db import connections
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse, resolve
from django.conf import settings


logger = logging.getLogger(__name__)


class SessionTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Processar a requisição antes da view
        if (
            hasattr(request, 'user')
            and request.user
            and request.user.is_authenticated
            and not isinstance(request.user, str)
        ):
            try:
                # Obter configurações baseadas no tenant atual
                if request.tenant.schema_name == get_public_schema_name():
                    # Schema público - usar ConfiguracaoSistema
                    configuracao = ConfiguracaoSistema.obter_configuracao()
                    tempo_maximo = configuracao.tempo_maximo_inatividade
                else:
                    # Schema do cliente - usar ClienteSystemSettings
                    configuracao = ClienteSystemSettings.obter_configuracao()
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
                        # Redirecionar para o login correto baseado no tenant
                        if request.tenant.schema_name == get_public_schema_name():
                            return redirect(reverse('login'))
                        else:
                            return redirect(reverse('LSCliente:clientelogin'))

                # Atualizar última atividade
                request.session['ultima_atividade'] = agora.isoformat()

                # NOVA LÓGICA: Rastrear sessão no contexto correto
                if hasattr(request, 'session') and request.session.session_key:
                    if request.tenant.schema_name == get_public_schema_name():
                        # Schema público - criar sessão no contexto público
                        SessaoUsuario.objects.update_or_create(
                            usuario=request.user,
                            chave_sessao=request.session.session_key,
                            defaults={
                                'ultima_atividade': agora,
                                'endereco_ip': self.get_client_ip(request),
                                'user_agent': request.META.get('HTTP_USER_AGENT', '')
                            }
                        )
                    else:
                        # Schema do cliente - criar sessão no contexto do cliente
                        # Mas usando o modelo SessaoUsuario que precisa existir no cliente também
                        from LSCliente.models import SessaoUsuarioCliente
                        SessaoUsuarioCliente.objects.update_or_create(
                            usuario=request.user,
                            chave_sessao=request.session.session_key,
                            defaults={
                                'ultima_atividade': agora,
                                'endereco_ip': self.get_client_ip(request),
                                'user_agent': request.META.get('HTTP_USER_AGENT', '')
                            }
                        )
                        
            except Exception as e:
                logger.error(f"[SessionTrackingMiddleware] Erro ao rastrear sessão: {e}")

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    


class TenantAccessControlMiddleware:
    """
    Middleware para controlar rigorosamente o acesso às views com base no tenant atual
    e redirecionar para a home correta.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = request.tenant
        current_path = request.path_info
        
        # Evitar bloquear acesso a arquivos estáticos e admin
        if current_path.startswith('/static/') or current_path.startswith('/admin/'):
            return self.get_response(request)
        
        # Obter as URLs corretas para o tenant atual
        if tenant.schema_name == get_public_schema_name():
            login_url = '/login/'
            home_url = reverse('home')
        else:
            login_url = '/clientelogin/'
            try:
                home_url = reverse('LSCliente:clientehome')
            except:
                home_url = '/home/'
                
        # IMPORTANTE: Verificar se o usuário está autenticado antes de fazer verificações adicionais
        # Evitar verificações para páginas de login, reset de senha e se o usuário já está autenticado
        if current_path == login_url or 'password_reset' in current_path or request.user.is_authenticated:
            return self.get_response(request)
            
        try:
            # Obter o nome da view atual
            resolver_match = resolve(current_path)
            view_name = resolver_match.view_name
            app_name = resolver_match.app_name
            namespace = resolver_match.namespace
            
            # Verificar se o usuário está acessando a raiz do site ('/')
            if current_path == '/':
                # Redirecionar com base no tenant, sem verificar autenticação
                if tenant.schema_name == get_public_schema_name():
                    if view_name != 'home' and view_name != 'login':
                        return HttpResponseRedirect(home_url)
                else:
                    if view_name != 'LSCliente:clientehome' and 'clientehome' not in view_name:
                        return HttpResponseRedirect(home_url)
            
            # Definir views exclusivas de cada tipo de tenant
            master_views = ['login', 'password_reset', 'collabmanage',
                        'collabregister', 'ClienteRegister', 'questao_manage', 
                        'ClienteEdit', 'configuracao_sistema', 'encerrar_sessao']
            
            # Verificar acesso com base no tenant
            if tenant.schema_name == get_public_schema_name():
                # No tenant público (master)
                if (namespace and namespace == 'LSCliente') or 'cliente' in view_name:
                    # Redirecionar para a página inicial do master ou login
                    if request.user.is_authenticated:
                        return HttpResponseRedirect(home_url)
                    else:
                        return HttpResponseRedirect(login_url)
            else:
                # Em tenants de cliente
                if view_name in master_views or (view_name == 'home' and not namespace):
                    # Se for uma view do LSDash, redirecionar para login do cliente
                    return HttpResponseRedirect(login_url)
                    
        except Exception as e:
            logger.error(f"Erro no middleware: {str(e)}")
            pass
                
        return self.get_response(request)

class TenantAwareSettingsMiddleware:
    """
    Middleware que ajusta dinamicamente as configurações de login e redirecionamento 
    com base no tenant atual.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = request.tenant
        
        # Ajustar as configurações de login dinamicamente
        if tenant.schema_name == get_public_schema_name():
            # No tenant público (master)
            settings.LOGIN_URL = '/login/'
            settings.LOGIN_REDIRECT_URL = 'home'
        else:
            # Em tenants de cliente
            settings.LOGIN_URL = '/clientelogin/'
            # Usar a URL nomeada em vez do caminho direto
            settings.LOGIN_REDIRECT_URL = 'LSCliente:clientehome'  # Use a URL nomeada
        
        # Continuar com a requisição normalmente
        response = self.get_response(request)
        return response

class SessionDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"[SESSION DEBUG] Tenant: {request.tenant.schema_name}")
        print(f"[SESSION DEBUG] Path: {request.path}")
        print(f"[SESSION DEBUG] User authenticated: {request.user.is_authenticated}")
        if request.user.is_authenticated:
            
            print(f"[SESSION DEBUG] User email: {request.user.email}")
        print(f"[SESSION DEBUG] Session key: {request.session.session_key}")
        print(f"[SESSION DEBUG] Session items: {request.session.items()}")
        
        response = self.get_response(request)
        return response