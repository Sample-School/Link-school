from django.contrib.auth import get_user_model
from django_tenants.utils import get_public_schema_name, get_tenant_model
from threading import local

# Thread local storage para manter o tenant atual
thread_locals = local()

def get_current_tenant():
    """
    Retorna o tenant atual da thread, com fallback para conexão atual
    """
    try:
        return thread_locals.tenant
    except AttributeError:
        # Se não tiver tenant no thread_locals, tenta pegar da conexão
        from django.db import connection
        
        if hasattr(connection, 'tenant'):
            return connection.tenant
            
        # Último recurso: busca o tenant público padrão
        TenantModel = get_tenant_model()
        try:
            default_tenant = TenantModel.objects.get(schema_name='public')
            return default_tenant
        except (TenantModel.DoesNotExist, TenantModel.MultipleObjectsReturned):
            return None

class TenantAwareAuthBackend:
    """
    Backend de autenticação que funciona com django-tenants.
    Autentica usuários diferentes baseado no schema/tenant atual.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if request is None:
            return None
            
        tenant = request.tenant
        tenant_name = tenant.schema_name
        
        print(f"Autenticando no tenant: {tenant_name}")
        
        try:
            # Normaliza o username/email para lowercase
            username = username.lower() if username else None
            print(f"Buscando usuário: {username}")
            
            if tenant.schema_name == get_public_schema_name():
                # Schema público - usa o User padrão do Django
                User = get_user_model()
                try:
                    user = User.objects.get(email=username)
                except User.DoesNotExist:
                    return None
            else:
                # Schema de cliente - usa o modelo customizado
                from LSCliente.models import UsuarioCliente
                try:
                    user = UsuarioCliente.objects.get(email=username)
                except UsuarioCliente.DoesNotExist:
                    return None
            
            print(f"Usuário encontrado: {user.id} - {user.email}")
            
            # Verifica se a senha está correta
            if user.check_password(password):
                print("Senha validada com sucesso")
                
                # Define o backend usado (necessário para o Django)
                if not hasattr(user, 'backend'):
                    user.backend = f"{self.__module__}.{self.__class__.__name__}"
                
                return user
            else:
                print("Senha incorreta")
                return None
                
        except Exception as e:
            print(f"Erro na autenticação: {str(e)}")
            return None
    
    def get_user(self, user_id):
        """
        Recupera um usuário pelo ID, considerando o tenant atual
        """
        tenant = get_current_tenant()
        
        if not tenant:
            return None
        
        if tenant.schema_name == get_public_schema_name():
            # Schema público
            User = get_user_model()
            try:
                return User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return None
        else:
            # Schema de cliente
            from LSCliente.models import UsuarioCliente
            try:
                return UsuarioCliente.objects.get(pk=user_id)
            except UsuarioCliente.DoesNotExist:
                return None