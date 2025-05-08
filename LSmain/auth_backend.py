from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
import inspect
from django.contrib.auth import get_user_model
from django_tenants.utils import get_public_schema_name
from django_tenants.utils import get_tenant_model, schema_context, tenant_context
from threading import local

# In auth_backend.py
from django_tenants.utils import get_tenant_model, get_tenant_domain_model
from threading import local

# Use this if you don't already have it defined
thread_locals = local()

def get_current_tenant():
    try:
        return thread_locals.tenant
    except AttributeError:
        # Fallback method when tenant isn't in thread_locals
        # Use the proper django-tenants methods to get tenant
        from django.db import connection
        
        # If using django-tenants, the connection should have the tenant schema set
        if hasattr(connection, 'tenant'):
            return connection.tenant
            
        # If no tenant in connection, try to get the default tenant
        TenantModel = get_tenant_model()
        try:
            default_tenant = TenantModel.objects.get(schema_name='public')
            return default_tenant
        except (TenantModel.DoesNotExist, TenantModel.MultipleObjectsReturned):
            # Handle case where there's no default tenant or multiple defaults
            return None

class TenantAwareAuthBackend:
    """
    Backend de autenticação consciente de tenant.
    """
    

    def authenticate(self, request, username=None, password=None, **kwargs):
        if request is None:
            return None
            
        tenant = request.tenant
        tenant_name = tenant.schema_name
        
        print(f"TenantAwareAuthBackend: Autenticando no tenant {tenant_name}")
        
        try:
            # Normalizar username/email
            username = username.lower() if username else None
            print(f"TenantAwareAuthBackend: Buscando usuário com email/username: {username}")
            
            if tenant.schema_name == get_public_schema_name():
                # No schema público (master), usamos o UserModel padrão
                User = get_user_model()
                try:
                    user = User.objects.get(email=username)
                except User.DoesNotExist:
                    return None
            else:
                # Nos schemas de clientes, usamos o UsuarioCliente
                from LSCliente.models import UsuarioCliente
                try:
                    user = UsuarioCliente.objects.get(email=username)
                except UsuarioCliente.DoesNotExist:
                    return None
            
            print(f"TenantAwareAuthBackend: Usuário encontrado: {user.id}, {user.email}")
            
            # Verificar a senha
            if user.check_password(password):
                print(f"TenantAwareAuthBackend: Senha verificada com sucesso")
                
                # Importante: Garantir que os atributos necessários estejam presentes
                if not hasattr(user, 'backend'):
                    user.backend = f"{self.__module__}.{self.__class__.__name__}"
                
                return user
            else:
                print(f"TenantAwareAuthBackend: Senha incorreta")
                return None
                
        except Exception as e:
            print(f"TenantAwareAuthBackend: Erro na autenticação: {str(e)}")
            return None
    
    def get_user(self, user_id):
        tenant = get_current_tenant()
        
        if tenant.schema_name == get_public_schema_name():
            # No schema público (master)
            User = get_user_model()
            try:
                return User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return None
        else:
            # Nos schemas de clientes
            from LSCliente.models import UsuarioCliente
            try:
                return UsuarioCliente.objects.get(pk=user_id)
            except UsuarioCliente.DoesNotExist:
                return None