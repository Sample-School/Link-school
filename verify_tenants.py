#!/usr/bin/env python
# Salve como verify_tenants.py e execute com python verify_tenants.py

import os
import django
import sys

# Configurar o ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LSmain.settings")
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model, get_tenant_domain_model, get_public_schema_name

Cliente = get_tenant_model()
Dominio = get_tenant_domain_model()

def main():
    print("\n=== VERIFICAÇÃO DE TENANTS E DOMÍNIOS ===\n")
    
    # Verificar schema público
    public_schema_name = get_public_schema_name()
    print(f"Schema público: {public_schema_name}")
    
    # Listar todos os tenants
    tenants = Cliente.objects.all()
    print(f"\nTotal de tenants: {tenants.count()}")
    
    for tenant in tenants:
        print(f"\nTenant: {tenant.nome if hasattr(tenant, 'nome') else tenant}")
        print(f"  Schema: {tenant.schema_name}")
        print(f"  É público: {'Sim' if tenant.schema_name == public_schema_name else 'Não'}")
        
        # Listar domínios associados a este tenant
        dominios = Dominio.objects.filter(tenant=tenant)
        print(f"  Domínios ({dominios.count()}):")
        
        for dominio in dominios:
            print(f"    - {dominio.domain}")
    
    # Verificar schemas no banco de dados
    with connection.cursor() as cursor:
        cursor.execute("SELECT schema_name FROM information_schema.schemata")
        schemas = [row[0] for row in cursor.fetchall()]
    
    print("\n=== SCHEMAS NO BANCO DE DADOS ===")
    for schema in schemas:
        # Mostrar apenas schemas relevantes (não mostrar schemas do sistema)
        if schema not in ['information_schema', 'pg_catalog', 'pg_toast']:
            tenant_exists = Cliente.objects.filter(schema_name=schema).exists()
            print(f"  - {schema} {'(Associado a um tenant)' if tenant_exists else '(Não associado!)'}")

if __name__ == "__main__":
    main()