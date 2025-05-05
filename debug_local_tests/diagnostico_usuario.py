import os
import django
import sys
from datetime import date, timedelta

# Configurar o ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LSmain.settings")
django.setup()

from LSDash.models import Cliente, Dominio
from django_tenants.utils import tenant_context
from django.contrib.auth import authenticate
import argparse
from django.http import HttpRequest  # Importar para criar request mock

def verificar_usuario_tenant(nome_tenant="finalteste", email="sampletxttest@gmail.com", senha="sample9090"):
    """
    Verifica se o usuário existe no tenant especificado e se suas credenciais funcionam.
    """
    # Buscar o tenant pelo nome
    try:
        tenant = Cliente.objects.get(nome=nome_tenant)
        print(f"Tenant encontrado: {tenant.nome} (schema: {tenant.schema_name})")
    except Cliente.DoesNotExist:
        print(f"Tenant '{nome_tenant}' não encontrado")
        return
    
    # Criar um request mock para autenticação
    mock_request = HttpRequest()
    mock_request.META = {'HTTP_HOST': f'{tenant.schema_name}.localhost'}  # Simular host para multitenancy
    
    # Verificar usuários no tenant
    with tenant_context(tenant):
        from LSCliente.models import UsuarioCliente
        
        # Verificar se o usuário existe
        try:
            usuario = UsuarioCliente.objects.get(email=email)
            print(f"Usuário encontrado: ID={usuario.id}, Nome={usuario.nome}, Email={usuario.email}")
            print(f"Status: {'Ativo' if usuario.is_active else 'Inativo'}")
            print(f"Permissões: Master={usuario.is_master}, Staff={usuario.is_staff}, Admin={usuario.is_superuser}")
            
            # Verificar o hash da senha (apenas para informação)
            print(f"Hash da senha existente: {usuario.password[:20]}...")
            
            # Testar autenticação direto no modelo
            print("\nTestando autenticação usando o método check_password...")
            if usuario.check_password(senha):
                print("✓ Senha correta conforme método check_password")
            else:
                print("✗ Senha incorreta conforme método check_password")
            
            # Testar com a função authenticate do Django (AGORA COM REQUEST)
            print("\nTestando autenticação com a função authenticate do Django...")
            auth_user = authenticate(request=mock_request, username=email, password=senha)
            if auth_user:
                print(f"✓ Autenticação bem-sucedida usando authenticate()")
            else:
                print("✗ Falha na autenticação usando authenticate()")
                
            # Redefinir a senha manualmente para garantir
            print("\nRedefinindo a senha do usuário para garantir que esteja correta...")
            usuario.set_password(senha)
            usuario.save()
            print(f"Senha redefinida para '{senha}'")
            print(f"Novo hash da senha: {usuario.password[:20]}...")
            
            # Testar novamente após redefinir (COM REQUEST)
            print("\nTestando autenticação após redefinição da senha...")
            auth_user = authenticate(request=mock_request, username=email, password=senha)
            if auth_user:
                print(f"✓ Autenticação bem-sucedida após redefinição")
            else:
                print("✗ Falha na autenticação após redefinição")
                
            # Testar usando o formulário diretamente
            print("\nTestando autenticação usando o UserLoginForm...")
            try:
                from LSCliente.forms import UserLoginForm
                form_data = {'email': email, 'password': senha}
                form = UserLoginForm(data=form_data, request=mock_request)
                
                if form.is_valid():
                    form_user = form.get_user()
                    print(f"✓ Autenticação bem-sucedida usando o formulário")
                else:
                    print(f"✗ Falha na autenticação usando o formulário: {form.errors}")
            except Exception as e:
                print(f"Erro ao testar formulário: {str(e)}")
            
        except UsuarioCliente.DoesNotExist:
            print(f"Usuário com email '{email}' não encontrado no tenant '{nome_tenant}'")
            
            # Se não existir, mostrar quais usuários existem
            usuarios = UsuarioCliente.objects.all()
            if usuarios:
                print("\nUsuários existentes neste tenant:")
                for u in usuarios:
                    print(f"- ID={u.id}, Nome={u.nome}, Email={u.email}, Ativo={u.is_active}")
            else:
                print("Não há usuários cadastrados neste tenant.")
            
            # Perguntar se deseja criar o usuário
            print("\nDeseja criar um novo usuário administrador?")
            resposta = input("Digite 'sim' para confirmar: ")
            
            if resposta.lower() == 'sim':
                # Criar o usuário
                try:
                    novo_usuario = UsuarioCliente.objects.create_superuser(
                        email=email,
                        nome=email.split('@')[0],
                        password=senha
                    )
                    print(f"Usuário criado com sucesso: ID={novo_usuario.id}, Email={novo_usuario.email}")
                except Exception as e:
                    print(f"Erro ao criar usuário: {str(e)}")
            
        # Verificar também o UserLoginForm e como ele está configurado
        print("\nVerificando a classe do formulário de login...")
        try:
            from LSCliente.forms import UserLoginForm
            print("Formulário UserLoginForm encontrado")
            
            # Verificar como o formulário está implementado
            import inspect
            try:
                source = inspect.getsource(UserLoginForm)
                print("\nImplementação do UserLoginForm:")
                print("---------------------------------")
                print(source)
                print("---------------------------------")
            except Exception as e:
                print(f"Não foi possível obter o código fonte do UserLoginForm: {str(e)}")
                
        except ImportError:
            print("Formulário UserLoginForm não encontrado no caminho esperado")

if __name__ == "__main__":
    # Configurar parser de argumentos para permitir personalização via linha de comando
    parser = argparse.ArgumentParser(description='Verificar usuário em um tenant específico.')
    parser.add_argument('--tenant', default="finalteste", help='Nome do tenant')
    parser.add_argument('--email', default="sampletxttest@gmail.com", help='Email do usuário')
    parser.add_argument('--senha', default="sample9090", help='Senha do usuário')
    
    args = parser.parse_args()
    
    # Chamar a função com os argumentos da linha de comando
    verificar_usuario_tenant(
        nome_tenant=args.tenant,
        email=args.email,
        senha=args.senha
    )