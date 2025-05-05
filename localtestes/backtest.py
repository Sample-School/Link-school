import os
import django
import sys

# Configurar o ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LSmain.settings")
django.setup()

from LSDash.models import Cliente
from django_tenants.utils import tenant_context
from django.http import HttpRequest
import argparse

def testar_backend_diretamente(nome_tenant="finalteste", email="sampletxttest@gmail.com", senha="sample9090"):
    """
    Testa o backend de autenticação diretamente, sem usar a função authenticate.
    """
    print(f"TESTE DIRETO DO BACKEND DE AUTENTICAÇÃO NO TENANT: {nome_tenant}")
    print("-" * 50)
    
    # Importar o backend
    from LSmain.auth_backend import TenantAwareAuthBackend
    
    # Buscar o tenant pelo nome
    try:
        tenant = Cliente.objects.get(nome=nome_tenant)
        print(f"Tenant encontrado: {tenant.nome} (schema: {tenant.schema_name})")
    except Cliente.DoesNotExist:
        print(f"Tenant '{nome_tenant}' não encontrado")
        return
    
    # Criar request mock
    mock_request = HttpRequest()
    mock_request.META = {'HTTP_HOST': f'{tenant.schema_name}.localhost'}
    mock_request.tenant = tenant  # Importante: definir o tenant no request
    
    # Criar uma instância do backend
    backend = TenantAwareAuthBackend()
    
    # Fazer o contexto do tenant
    with tenant_context(tenant):
        # Testar authenticate diretamente
        user = backend.authenticate(
            request=mock_request,
            username=email,
            password=senha
        )
        
        if user:
            print(f"✓ Backend autenticou com sucesso. User ID: {user.id}, Email: {user.email}")
            
            # Testar get_user
            user_retrieved = backend.get_user(user.id)
            if user_retrieved:
                print(f"✓ Backend recuperou usuário com sucesso: {user_retrieved.email}")
            else:
                print(f"✗ Falha ao recuperar usuário com get_user")
        else:
            print(f"✗ Falha na autenticação usando o backend diretamente")
            
            # Verificar se o usuário existe
            try:
                from LSCliente.models import UsuarioCliente
                try:
                    usuario = UsuarioCliente.objects.get(email=email)
                    print(f"Usuário existe: ID={usuario.id}, Email={usuario.email}")
                    
                    # Testar senha diretamente
                    if usuario.check_password(senha):
                        print(f"✓ Senha correta conforme check_password")
                    else:
                        print(f"✗ Senha incorreta conforme check_password")
                        
                except UsuarioCliente.DoesNotExist:
                    print(f"Usuário não encontrado no tenant")
            except ImportError:
                print(f"Não foi possível importar o modelo UsuarioCliente")

def main():
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(description='Teste direto do backend de autenticação.')
    parser.add_argument('--tenant', default="finalteste", help='Nome do tenant')
    parser.add_argument('--email', default="sampletxttest@gmail.com", help='Email do usuário')
    parser.add_argument('--senha', default="sample9090", help='Senha do usuário')
    
    args = parser.parse_args()
    
    # Executar teste
    testar_backend_diretamente(
        nome_tenant=args.tenant,
        email=args.email,
        senha=args.senha
    )

if __name__ == "__main__":
    main()