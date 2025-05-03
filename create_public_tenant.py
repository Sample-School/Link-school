#!/usr/bin/env python
# Salve como create_public_tenant.py e execute com python create_public_tenant.py

import os
import django
import sys
from datetime import datetime, timedelta, date

# Configurar o ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LSmain.settings")
django.setup()

from django.db import connection
from django.utils import timezone
from LSDash.models import Cliente, Dominio, UsuarioMaster
from django_tenants.utils import get_public_schema_name

def criar_tenant_public():
    # Obter nome do schema público das configurações
    public_schema = get_public_schema_name()
    print(f"Schema público configurado: {public_schema}")
    
    # Verificar se o tenant do schema público já existe
    if Cliente.objects.filter(schema_name=public_schema).exists():
        print(f"O tenant público (schema: {public_schema}) já existe.")
        tenant = Cliente.objects.get(schema_name=public_schema)
    else:
        # Data de início hoje
        data_inicio = date.today()
        # Data de validade um ano no futuro
        data_validade = data_inicio + timedelta(days=365)
        
        # Criar o tenant público
        tenant = Cliente(
            schema_name=public_schema,
            nome="Master LinkSchool",
            data_inicio_assinatura=data_inicio,  # Adicionar data de início
            data_validade_assinatura=data_validade,  # Adicionar data de validade
            # Preencha outros campos obrigatórios do modelo Cliente
            cor_primaria="#000000",
            cor_secundaria="#FFFFFF",
            qtd_usuarios=5
        )
        
        # Salvar sem criar schema (o schema public já existe)
        tenant.auto_create_schema = False
        tenant.save()
        print(f"Tenant público '{tenant.nome}' criado com sucesso!")
        
        # Opcionalmente, criar um usuário master para este tenant
        # Descomente e ajuste o código abaixo se desejar criar um usuário master
        """
        usuario_master = UsuarioMaster.objects.create_user(
            email="admin@linkschool.com.br",
            password="senha123",  # Altere para uma senha segura
            cliente=tenant,
        )
        
        # Associar o usuário master ao tenant
        tenant.usuario_master = usuario_master
        tenant.save(update_fields=['usuario_master'])
        print(f"Usuário master criado para o tenant público: {usuario_master.email}")
        """
    
    # Verificar se já existe um domínio para localhost
    dominio = "localhost"
    
    if Dominio.objects.filter(domain=dominio).exists():
        print(f"O domínio '{dominio}' já existe.")
    else:
        # Adicionar domínio para o tenant público
        domain = Dominio(
            domain=dominio,
            tenant=tenant,
            is_primary=True
        )
        domain.save()
        print(f"Domínio '{dominio}' adicionado ao tenant público!")
    
    # Verificar se já existe um domínio para 127.0.0.1
    dominio_ip = "127.0.0.1"
    
    if Dominio.objects.filter(domain=dominio_ip).exists():
        print(f"O domínio '{dominio_ip}' já existe.")
    else:
        # Adicionar domínio IP para o tenant público
        domain_ip = Dominio(
            domain=dominio_ip,
            tenant=tenant,
            is_primary=False
        )
        domain_ip.save()
        print(f"Domínio '{dominio_ip}' adicionado ao tenant público!")
    
    print("\nInformações para acessar o tenant público:")
    print("URL: http://localhost:8000/ ou http://127.0.0.1:8000/")

if __name__ == "__main__":
    criar_tenant_public()