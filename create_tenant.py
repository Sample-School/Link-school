import os
import django
import sys
from datetime import date, timedelta

# Configurar o ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LSmain.settings")
django.setup()

from LSDash.models import Cliente, Dominio
from django.utils.text import slugify
from django.core.management import call_command
from django_tenants.utils import tenant_context
from django.core.files.base import ContentFile
import argparse

# Import your models (assuming these are from your project)
from LSDash.models import Cliente, Dominio  # Adjust imports according to your project structure

def criar_tenant_completo(nome="finalteste", 
                          email_master="sampletxttest@gmail.com", 
                          senha_master="sample9090",
                          subdominio=None,
                          cor_primaria="#3498db", 
                          cor_secundaria="#2ecc71",
                          data_inicio=None,
                          data_validade=None,
                          observacoes="Cliente criado via script",
                          qtd_usuarios=5,
                          logo_path=None,
                          substituir_existente=False):
    
    # Definir datas padrão se não forem fornecidas
    if data_inicio is None:
        data_inicio = date.today()
    if data_validade is None:
        data_validade = date.today() + timedelta(days=30)
    
    # Criar schema_name a partir do nome usando slugify
    schema_name = slugify(nome)
    
    # Se o subdomínio não for fornecido, criar um com base no schema_name
    if subdominio is None:
        subdominio = schema_name
    
    print(f"Criando tenant '{nome}' (schema: {schema_name})...")
    
    # Verificar se o tenant já existe (por schema_name ou nome)
    tenant_exists = False
    tenant = None
    
    # Verificar pelo schema_name
    if Cliente.objects.filter(schema_name=schema_name).exists():
        tenant_exists = True
        tenant = Cliente.objects.get(schema_name=schema_name)
        print(f"O tenant com schema '{schema_name}' já existe.")
    
    # Verificar pelo nome (que parece ter uma restrição de unicidade)
    elif Cliente.objects.filter(nome=nome).exists():
        tenant_exists = True
        tenant = Cliente.objects.get(nome=nome)
        print(f"O tenant com nome '{nome}' já existe (schema: {tenant.schema_name}).")
    
    if tenant_exists:
        if substituir_existente:
            print(f"Excluindo tenant existente '{nome}' conforme solicitado...")
            
            # Excluir domínios associados primeiro
            dominio_base = 'localhost'
            dominio_completo = f"{subdominio}.{dominio_base}"
            Dominio.objects.filter(tenant=tenant).delete()
            print(f"Domínios associados ao tenant foram excluídos.")
            
            # Excluir o tenant
            try:
                tenant.delete()
                print(f"Tenant excluído com sucesso!")
                # Garantir que não há registros residuais com o mesmo nome
                remaining = Cliente.objects.filter(nome=nome)
                if remaining.exists():
                    for t in remaining:
                        t.delete()
                    print(f"Registros residuais com nome '{nome}' também foram excluídos.")
            except Exception as e:
                print(f"Erro ao excluir tenant: {str(e)}")
                print("A operação de exclusão falhou. Tente excluir manualmente o tenant do banco de dados.")
                return
        else:
            print("Use a opção --substituir para excluir e recriar este tenant.")
            return
    
    # Criar o tenant
    try:
        # Preparar o logo se fornecido
        logo = None
        if logo_path and os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_content = f.read()
                logo = ContentFile(logo_content, name=os.path.basename(logo_path))
        
        # Criar o cliente com o usuário master usando o manager personalizado
        tenant = Cliente.objects.create_cliente_with_master(
            nome=nome,
            email_master=email_master,
            password_master=senha_master,
            cor_primaria=cor_primaria,
            cor_secundaria=cor_secundaria,
            data_inicio_assinatura=data_inicio,
            data_validade_assinatura=data_validade,
            observacoes=observacoes,
            logo=logo,
            qtd_usuarios=qtd_usuarios,
            schema_name=schema_name
        )
        print(f"Tenant '{nome}' criado com sucesso!")
    except Exception as e:
        print(f"Erro ao criar o tenant: {str(e)}")
        return
    
    # Configurar o domínio
    dominio_base = 'localhost'
    dominio_completo = f"{subdominio}.{dominio_base}"
    
    if Dominio.objects.filter(domain=dominio_completo).exists():
        print(f"O domínio '{dominio_completo}' já existe.")
    else:
        try:
            # Adicionar domínio para o tenant
            dominio = Dominio(
                domain=dominio_completo,
                tenant=tenant,
                is_primary=True
            )
            dominio.save()
            print(f"Domínio '{dominio_completo}' adicionado ao tenant '{nome}'!")
        except Exception as e:
            print(f"Erro ao configurar o domínio: {str(e)}")
            return
    
    # Executar migrações para o novo tenant
    print("Executando migrações para o novo tenant...")
    try:
        with tenant_context(tenant):
            call_command('migrate', '--schema', tenant.schema_name)
    except Exception as e:
        print(f"Erro ao executar migrações: {str(e)}")
        return
    
    # CORREÇÃO: Verificar e corrigir o email do usuário master dentro do tenant
    try:
        with tenant_context(tenant):
            from LSCliente.models import UsuarioCliente
            
            # Verificar todos os usuários administradores
            admin_users = UsuarioCliente.objects.filter(is_master=True)
            if admin_users.exists():
                for admin_user in admin_users:
                    if admin_user.email != email_master:
                        print(f"Corrigindo email do usuário admin de {admin_user.email} para {email_master}")
                        # Guardar o ID para garantir que estamos atualizando o mesmo usuário
                        user_id = admin_user.id
                        admin_user.email = email_master
                        # Atualizar também o campo nome se estiver usando o valor padrão
                        if admin_user.nome == nome or admin_user.nome == admin_user.email:
                            admin_user.nome = email_master.split('@')[0]
                        admin_user.save()
                        
                        # Confirmar que a atualização foi bem-sucedida
                        updated_user = UsuarioCliente.objects.get(id=user_id)
                        print(f"Email atualizado com sucesso: {updated_user.email}")
            else:
                print("Nenhum usuário administrador encontrado no tenant.")
                
                # Se não houver administrador, criar um novo
                print(f"Criando usuário master ({email_master}) dentro do tenant...")
                usuario_tenant = UsuarioCliente.objects.create_superuser(
                    email=email_master,
                    nome=email_master.split('@')[0],
                    password=senha_master
                )
                print("Usuário master criado com sucesso!")
    except Exception as e:
        print(f"Erro ao verificar/corrigir usuário master no tenant: {str(e)}")
    
    print("\nInformações para acessar o tenant:")
    print(f"URL: http://{dominio_completo}:8000/")
    print(f"Email: {email_master}")
    print(f"Senha: {senha_master}")
    print("Certifique-se de que seu arquivo /etc/hosts ou configuração DNS local mapeia este domínio para 127.0.0.1")

if __name__ == "__main__":
    # Configurar parser de argumentos para permitir personalização via linha de comando
    parser = argparse.ArgumentParser(description='Criar um tenant de teste com configurações completas.')
    parser.add_argument('--nome', default="finalteste", help='Nome do cliente/tenant')
    parser.add_argument('--email', default="sampletxttest@gmail.com", help='Email do usuário master')
    parser.add_argument('--senha', default="sample9090", help='Senha do usuário master')
    parser.add_argument('--subdominio', default=None, help='Subdomínio para acesso (se omitido, será derivado do nome)')
    parser.add_argument('--cor-primaria', default="#3498db", help='Cor primária no formato hex')
    parser.add_argument('--cor-secundaria', default="#2ecc71", help='Cor secundária no formato hex')
    parser.add_argument('--dias-validade', type=int, default=30, help='Dias de validade da assinatura')
    parser.add_argument('--observacoes', default="Cliente criado via script", help='Observações sobre o cliente')
    parser.add_argument('--qtd-usuarios', type=int, default=5, help='Quantidade de usuários permitidos')
    parser.add_argument('--logo', default=None, help='Caminho para o arquivo de logo')
    parser.add_argument('--substituir', action='store_true', help='Excluir e recriar o tenant se já existir')
    
    args = parser.parse_args()
    
    # Calcular datas com base nos argumentos
    data_inicio = date.today()
    data_validade = data_inicio + timedelta(days=args.dias_validade)
    
    # Chamar a função com os argumentos da linha de comando
    criar_tenant_completo(
        nome=args.nome,
        email_master=args.email,
        senha_master=args.senha,
        subdominio=args.subdominio,
        cor_primaria=args.cor_primaria,
        cor_secundaria=args.cor_secundaria,
        data_inicio=data_inicio,
        data_validade=data_validade,
        observacoes=args.observacoes,
        qtd_usuarios=args.qtd_usuarios,
        logo_path=args.logo,
        substituir_existente=args.substituir
    )