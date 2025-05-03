#!/usr/bin/env python
# Salve como create_tenant.py e execute com python create_tenant.py

import os
import django
import sys

# Configurar o ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LSmain.settings")
django.setup()

from LSDash.models import Cliente, Dominio
from datetime import date, timedelta

def criar_tenant_teste():
    # Verificar se o tenant já existe
    nome_tenant = "Cliente de Teste"
    schema_name = "cliente_teste"
    
    if Cliente.objects.filter(schema_name=schema_name).exists():
        print(f"O tenant '{nome_tenant}' (schema: {schema_name}) já existe.")
        tenant = Cliente.objects.get(schema_name=schema_name)
    else:
        # Criar o tenant
        tenant = Cliente(
            schema_name=schema_name,
            nome=nome_tenant,
            data_inicio_assinatura=date.today(),
            data_validade_assinatura=date.today() + timedelta(days=30),
            # Adicione aqui outros campos necessários para seu modelo Cliente
        )
        tenant.save()
        print(f"Tenant '{nome_tenant}' criado com sucesso!")
    
    # Verificar se o domínio já existe
    dominio = "clienteteste.localhost"
    
    if Dominio.objects.filter(domain=dominio).exists():
        print(f"O domínio '{dominio}' já existe.")
    else:
        # Adicionar domínio para o tenant
        domain = Dominio(
            domain=dominio,
            tenant=tenant,
            is_primary=True
        )
        domain.save()
        print(f"Domínio '{dominio}' adicionado ao tenant '{nome_tenant}'!")
    
    print("\nInformações para acessar o tenant:")
    print(f"URL: http://{dominio}:8000/")
    print("Certifique-se de que seu arquivo /etc/hosts ou configuração DNS local mapeia este domínio para 127.0.0.1")

if __name__ == "__main__":
    criar_tenant_teste()