#!/usr/bin/env python
# Script para criar tenants completos com usuário master - execute com: python create_tenant_completo.py

import os
import django
import argparse
from datetime import date, timedelta

# Configura o ambiente Django antes de importar os models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LSmain.settings")
django.setup()

from LSDash.models import Cliente, Dominio
from django.utils.text import slugify
from django.core.management import call_command
from django_tenants.utils import tenant_context
from django.core.files.base import ContentFile

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
    """
    Cria um tenant completo com usuário master e configurações personalizadas.
    Inclui verificação de existência, criação de domínio e execução de migrações.
    """
    
    # Define datas padrão caso não sejam informadas
    if data_inicio is None:
        data_inicio = date.today()
    if data_validade is None:
        data_validade = date.today() + timedelta(days=30)
    
    # Gera o schema_name baseado no nome do tenant
    schema_name = slugify(nome)
    
    # Se não informar subdomínio, usa o mesmo nome do schema
    if subdominio is None:
        subdominio = schema_name
    
    print(f"Iniciando criação do tenant '{nome}' (schema: {schema_name})...")
    
    # Verifica se já existe um tenant com esse nome ou schema
    tenant_exists = False
    tenant = None
    
    if Cliente.objects.filter(schema_name=schema_name).exists():
        tenant_exists = True
        tenant = Cliente.objects.get(schema_name=schema_name)
        print(f"Já existe um tenant com o schema '{schema_name}'")
    elif Cliente.objects.filter(nome=nome).exists():
        tenant_exists = True
        tenant = Cliente.objects.get(nome=nome)
        print(f"Já existe um tenant com o nome '{nome}' (schema: {tenant.schema_name})")
    
    # Se existe e foi solicitado para substituir, exclui o tenant antigo
    if tenant_exists:
        if substituir_existente:
            print(f"Removendo tenant existente '{nome}' conforme solicitado...")
            
            # Remove os domínios associados primeiro
            dominio_base = 'localhost'
            dominio_completo = f"{subdominio}.{dominio_base}"
            Dominio.objects.filter(tenant=tenant).delete()
            print("Domínios associados foram removidos")
            
            # Remove o tenant
            try:
                tenant.delete()
                print("Tenant anterior removido com sucesso!")
                
                # Limpa qualquer registro residual
                remaining = Cliente.objects.filter(nome=nome)
                if remaining.exists():
                    for t in remaining:
                        t.delete()
                    print("Registros residuais também foram limpos")
                    
            except Exception as e:
                print(f"Erro ao remover tenant: {str(e)}")
                print("Falha na remoção. Tente excluir manualmente do banco")
                return
        else:
            print("Para substituir um tenant existente, use a opção --substituir")
            return
    
    # Cria o novo tenant
    try:
        # Processa o logo se foi fornecido um arquivo
        logo = None
        if logo_path and os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_content = f.read()
                logo = ContentFile(logo_content, name=os.path.basename(logo_path))
        
        # Usa o manager personalizado para criar cliente com usuário master
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
        print(f"Erro na criação do tenant: {str(e)}")
        return
    
    # Configura o domínio de acesso
    dominio_base = 'localhost'
    dominio_completo = f"{subdominio}.{dominio_base}"
    
    if Dominio.objects.filter(domain=dominio_completo).exists():
        print(f"Domínio '{dominio_completo}' já está configurado")
    else:
        try:
            # Cria o registro de domínio para o tenant
            dominio = Dominio(
                domain=dominio_completo,
                tenant=tenant,
                is_primary=True
            )
            dominio.save()
            print(f"Domínio '{dominio_completo}' configurado para o tenant")
            
        except Exception as e:
            print(f"Erro ao configurar domínio: {str(e)}")
            return
    
    # Executa as migrações necessárias no novo tenant
    print("Aplicando migrações no novo tenant...")
    try:
        with tenant_context(tenant):
            call_command('migrate', '--schema', tenant.schema_name)
    except Exception as e:
        print(f"Erro ao aplicar migrações: {str(e)}")
        return
    
    # Verifica e corrige o usuário master dentro do contexto do tenant
    try:
        with tenant_context(tenant):
            from LSCliente.models import UsuarioCliente
            
            # Busca usuários administradores no tenant
            admin_users = UsuarioCliente.objects.filter(is_master=True)
            
            if admin_users.exists():
                for admin_user in admin_users:
                    # Corrige o email se estiver diferente do solicitado
                    if admin_user.email != email_master:
                        print(f"Corrigindo email: {admin_user.email} → {email_master}")
                        user_id = admin_user.id
                        admin_user.email = email_master
                        
                        # Atualiza o nome se estiver usando valor padrão
                        if admin_user.nome == nome or admin_user.nome == admin_user.email:
                            admin_user.nome = email_master.split('@')[0]
                        
                        admin_user.save()
                        
                        # Confirma que a atualização funcionou
                        updated_user = UsuarioCliente.objects.get(id=user_id)
                        print(f"Email atualizado: {updated_user.email}")
            else:
                # Se não tem admin, cria um novo usuário master
                print("Nenhum usuário master encontrado, criando um novo...")
                usuario_tenant = UsuarioCliente.objects.create_superuser(
                    email=email_master,
                    nome=email_master.split('@')[0],
                    password=senha_master
                )
                print("Usuário master criado dentro do tenant!")
                
    except Exception as e:
        print(f"Erro ao configurar usuário master: {str(e)}")
    
    # Exibe informações de acesso
    print("\n" + "="*60)
    print("TENANT CRIADO COM SUCESSO!")
    print("="*60)
    print(f"URL de acesso: http://{dominio_completo}:8000/")
    print(f"Email de login: {email_master}")
    print(f"Senha: {senha_master}")
    print("="*60)
    print("IMPORTANTE: Configure seu /etc/hosts para mapear")
    print(f"{dominio_completo} → 127.0.0.1")
    print("="*60)

if __name__ == "__main__":
    # Configura os argumentos da linha de comando
    parser = argparse.ArgumentParser(description='Criar tenant completo com configurações personalizadas')
    
    parser.add_argument('--nome', default="finalteste", 
                       help='Nome do cliente/tenant')
    parser.add_argument('--email', default="sampletxttest@gmail.com", 
                       help='Email do usuário master')
    parser.add_argument('--senha', default="sample9090", 
                       help='Senha do usuário master')
    parser.add_argument('--subdominio', default=None, 
                       help='Subdomínio para acesso (padrão: deriva do nome)')
    parser.add_argument('--cor-primaria', default="#3498db", 
                       help='Cor primária em formato hex')
    parser.add_argument('--cor-secundaria', default="#2ecc71", 
                       help='Cor secundária em formato hex')
    parser.add_argument('--dias-validade', type=int, default=30, 
                       help='Dias de validade da assinatura')
    parser.add_argument('--observacoes', default="Cliente criado via script", 
                       help='Observações sobre o cliente')
    parser.add_argument('--qtd-usuarios', type=int, default=5, 
                       help='Quantidade máxima de usuários')
    parser.add_argument('--logo', default=None, 
                       help='Caminho para arquivo de logo')
    parser.add_argument('--substituir', action='store_true', 
                       help='Remove e recria o tenant se já existir')
    
    args = parser.parse_args()
    
    # Calcula as datas baseado nos argumentos
    data_inicio = date.today()
    data_validade = data_inicio + timedelta(days=args.dias_validade)
    
    # Executa a criação do tenant
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