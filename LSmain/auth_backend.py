from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
import inspect

class TenantAwareAuthBackend(ModelBackend):
    """
    Backend de autenticação que é ciente dos diferentes modelos de usuário
    para diferentes tenants.
    """
    
    def authenticate(self, request=None, username=None, password=None, **kwargs):
        # Salvar a referência do request para uso posterior no get_user
        self._request = request
        
        # Verificar se temos um request válido com informações de tenant
        if request and hasattr(request, 'tenant') and request.tenant and request.tenant.schema_name != 'public':
            # Estamos em um tenant cliente
            try:
                # Importação aqui para evitar problemas de circular import
                from LSCliente.models import UsuarioCliente
                
                # Log para depuração
                print(f"TenantAwareAuthBackend: Autenticando no tenant {request.tenant.schema_name}")
                print(f"TenantAwareAuthBackend: Buscando usuário com email/username: {username}")
                
                # Busca o usuário pelo email no modelo UsuarioCliente
                try:
                    # Tenta pelo email primeiro
                    user = UsuarioCliente.objects.get(email=username)
                    
                    # Log para depuração
                    print(f"TenantAwareAuthBackend: Usuário encontrado: {user.id}, {user.email}")
                    
                    # Verifica a senha
                    if user.check_password(password):
                        print(f"TenantAwareAuthBackend: Senha verificada com sucesso")
                        return user
                    else:
                        print(f"TenantAwareAuthBackend: Senha incorreta")
                        return None
                        
                except UsuarioCliente.DoesNotExist:
                    # Usuário não encontrado neste tenant
                    print(f"TenantAwareAuthBackend: Usuário não encontrado no tenant {request.tenant.schema_name}")
                    return None
                    
            except ImportError as e:
                # Falha ao importar o modelo do cliente
                print(f"TenantAwareAuthBackend: Erro ao importar UsuarioCliente: {e}")
                return None
        else:
            # Estamos no schema public/master ou request não tem tenant
            if request and hasattr(request, 'tenant'):
                print(f"TenantAwareAuthBackend: Autenticando no schema master/public")
            else:
                print(f"TenantAwareAuthBackend: Request não tem tenant ou é None")
                
            UserModel = get_user_model()
            try:
                # Busca o usuário pelo email ou username no modelo UserModel
                user = UserModel.objects.get(
                    Q(username=username) | Q(email=username)
                )
                
                if user.check_password(password):
                    return user
            except UserModel.DoesNotExist:
                # Usuário não encontrado no tenant master
                return None
                
        return None
        
    def get_user(self, user_id):
        """
        Retorna o usuário pelo ID, dependendo do tenant atual.
        """
        # Verifica se temos acesso ao request que foi salvo no authenticate
        if hasattr(self, '_request') and self._request and hasattr(self._request, 'tenant') and self._request.tenant.schema_name != 'public':
            # Em um tenant cliente
            try:
                from LSCliente.models import UsuarioCliente
                print(f"TenantAwareAuthBackend.get_user: Buscando usuário com ID {user_id} no tenant {self._request.tenant.schema_name}")
                user = UsuarioCliente.objects.get(pk=user_id)
                print(f"TenantAwareAuthBackend.get_user: Usuário encontrado: {user.email}")
                return user
            except (ImportError, UsuarioCliente.DoesNotExist) as e:
                print(f"TenantAwareAuthBackend.get_user: Erro ao buscar usuário: {e}")
                return None
        else:
            # No tenant master ou request não disponível
            UserModel = get_user_model()
            try:
                return UserModel.objects.get(pk=user_id)
            except UserModel.DoesNotExist:
                return None

    def has_perm(self, user_obj, perm, obj=None):
        # Implementar verificação de permissões específica para tenant
        # Se o usuário for do tipo UsuarioCliente, usar lógica específica
        if hasattr(self, '_request') and hasattr(self._request, 'tenant') and self._request.tenant.schema_name != 'public':
            # Verificar se é um usuário do tenant
            if hasattr(user_obj, 'is_master') and user_obj.is_master:
                return True
        
        # Caso contrário, usar a lógica padrão
        return super().has_perm(user_obj, perm, obj)