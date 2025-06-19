from django_tenants.middleware import TenantMainMiddleware
from LSDash.models import Dominio, ConfiguracaoSistema, SessaoUsuario
from LSCliente.models import ClienteSystemSettings
from django.utils import timezone
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse, resolve
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django_tenants.utils import get_public_schema_name
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SessionTrackingMiddleware:
    """
    Middleware para rastrear sessões de usuários e controlar tempo de inatividade
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (hasattr(request, 'user') and request.user and 
            request.user.is_authenticated and not isinstance(request.user, str)):
            try:
                # Busca configuração baseada no tenant atual
                if request.tenant.schema_name == get_public_schema_name():
                    configuracao = ConfiguracaoSistema.obter_configuracao()
                    tempo_maximo = configuracao.tempo_maximo_inatividade
                else:
                    configuracao = ClienteSystemSettings.obter_configuracao()
                    tempo_maximo = configuracao.tempo_maximo_inatividade

                # Verifica se a sessão expirou por inatividade
                ultima_atividade = request.session.get('ultima_atividade')
                agora = timezone.now()

                if ultima_atividade:
                    ultima_atividade = timezone.datetime.fromisoformat(ultima_atividade)
                    if (agora - ultima_atividade).total_seconds() > (tempo_maximo * 60):
                        logout(request)
                        messages.warning(request, "Sua sessão expirou devido à inatividade.")
                        
                        # Redireciona para o login correto
                        if request.tenant.schema_name == get_public_schema_name():
                            return redirect(reverse('login'))
                        else:
                            return redirect(reverse('LSCliente:clientelogin'))

                # Atualiza timestamp da última atividade
                request.session['ultima_atividade'] = agora.isoformat()

                # Registra a sessão no modelo correto baseado no tenant
                if hasattr(request, 'session') and request.session.session_key:
                    if request.tenant.schema_name == get_public_schema_name():
                        # Schema público
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
                        # Schema de cliente
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
                logger.error(f"Erro ao rastrear sessão: {e}")

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """Extrai o IP real do cliente considerando proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TenantAccessControlMiddleware:
    """
    Controla acesso às views baseado no tenant atual.
    Evita que usuários acessem views de outros tenants.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = request.tenant
        current_path = request.path_info
        
        # Libera acesso para arquivos estáticos e admin
        if current_path.startswith('/static/') or current_path.startswith('/admin/'):
            return self.get_response(request)
        
        # Define URLs corretas para cada tenant
        if tenant.schema_name == get_public_schema_name():
            login_url = '/login/'
            home_url = reverse('home')
        else:
            login_url = '/clientelogin/'
            try:
                home_url = reverse('LSCliente:clientehome')
            except:
                home_url = '/home/'
                
        # Permite acesso a login, reset de senha e se já autenticado
        if (current_path == login_url or 'password_reset' in current_path or 
            request.user.is_authenticated):
            return self.get_response(request)
            
        try:
            resolver_match = resolve(current_path)
            view_name = resolver_match.view_name
            app_name = resolver_match.app_name
            namespace = resolver_match.namespace
            
            # Redireciona raiz do site baseado no tenant
            if current_path == '/':
                if tenant.schema_name == get_public_schema_name():
                    if view_name != 'home' and view_name != 'login':
                        return HttpResponseRedirect(home_url)
                else:
                    if view_name != 'LSCliente:clientehome' and 'clientehome' not in view_name:
                        return HttpResponseRedirect(home_url)
            
            # Views exclusivas do tenant master
            master_views = ['login', 'password_reset', 'collabmanage',
                           'collabregister', 'ClienteRegister', 'questao_manage', 
                           'ClienteEdit', 'configuracao_sistema', 'encerrar_sessao']
            
            # Controla acesso baseado no tipo de tenant
            if tenant.schema_name == get_public_schema_name():
                # Tenant público - bloqueia acesso a views de cliente  
                if (namespace and namespace == 'LSCliente') or 'cliente' in view_name:
                    if request.user.is_authenticated:
                        return HttpResponseRedirect(home_url)
                    else:
                        return HttpResponseRedirect(login_url)
            else:
                # Tenant de cliente - bloqueia views do master
                if view_name in master_views or (view_name == 'home' and not namespace):
                    return HttpResponseRedirect(login_url)
                    
        except Exception as e:
            logger.error(f"Erro no middleware de controle de acesso: {str(e)}")
            pass
                
        return self.get_response(request)


class TenantAwareSettingsMiddleware:
    """
    Ajusta configurações de login dinamicamente baseado no tenant atual
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = request.tenant
        
        # Configura URLs de login baseadas no tenant
        if tenant.schema_name == get_public_schema_name():
            settings.LOGIN_URL = '/login/'
            settings.LOGIN_REDIRECT_URL = 'home'
        else:
            settings.LOGIN_URL = '/clientelogin/'
            settings.LOGIN_REDIRECT_URL = 'LSCliente:clientehome'
        
        response = self.get_response(request)
        return response


class SessionDebugMiddleware:
    """
    Middleware para debug de sessões (remover em produção)
    """
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