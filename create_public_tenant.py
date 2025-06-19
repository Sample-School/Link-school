
# Script para criar o tenant público - execute com: python create_public_tenant.py

import os
import django
from datetime import timedelta, date

# Configura o ambiente Django antes de importar os models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LSmain.settings")
django.setup()

from LSDash.models import Cliente, Dominio, UsuarioMaster
from django_tenants.utils import get_public_schema_name

def criar_tenant_public():
    """
    Cria o tenant público necessário para o funcionamento do sistema multi-tenant.
    Este tenant será usado como base para o schema público do banco de dados.
    """
    # Pega o nome do schema público das configurações do django-tenants
    public_schema = get_public_schema_name()
    print(f"Schema público configurado: {public_schema}")
    
    # Verifica se já existe um tenant com esse schema
    if Cliente.objects.filter(schema_name=public_schema).exists():
        print(f"Tenant público já existe no schema: {public_schema}")
        tenant = Cliente.objects.get(schema_name=public_schema)
    else:
        # Define as datas de assinatura - hoje e válido por 1 ano
        data_inicio = date.today()
        data_validade = data_inicio + timedelta(days=365)
        
        # Cria o registro do tenant público
        tenant = Cliente(
            schema_name=public_schema,
            nome="Master LinkSchool",
            data_inicio_assinatura=data_inicio,
            data_validade_assinatura=data_validade,
            cor_primaria="#000000",
            cor_secundaria="#FFFFFF",
            qtd_usuarios=5
        )
        
        # O schema 'public' já existe no banco, não precisa criar
        tenant.auto_create_schema = False
        tenant.save()
        print(f"Tenant público '{tenant.nome}' criado com sucesso!")
        
        # Se precisar criar um usuário master, descomente o bloco abaixo
        """
        usuario_master = UsuarioMaster.objects.create_user(
            email="admin@linkschool.com.br",
            password="senha123",  # Lembre-se de usar uma senha forte em produção
            cliente=tenant,
        )
        
        tenant.usuario_master = usuario_master
        tenant.save(update_fields=['usuario_master'])
        print(f"Usuário master criado: {usuario_master.email}")
        """
    
    # Configura os domínios para desenvolvimento local
    dominios_config = [
        {"domain": "localhost", "is_primary": True},
        {"domain": "127.0.0.1", "is_primary": False}
    ]
    
    for config in dominios_config:
        dominio = config["domain"]
        
        if Dominio.objects.filter(domain=dominio).exists():
            print(f"Domínio '{dominio}' já está configurado")
        else:
            # Adiciona o domínio ao tenant público
            domain = Dominio(
                domain=dominio,
                tenant=tenant,
                is_primary=config["is_primary"]
            )
            domain.save()
            print(f"Domínio '{dominio}' adicionado ao tenant público")
    
    print("\n" + "="*50)
    print("CONFIGURAÇÃO CONCLUÍDA")
    print("="*50)
    print("Acesse o sistema através de:")
    print("• http://localhost:8000/")
    print("• http://127.0.0.1:8000/")
    print("="*50)

if __name__ == "__main__":
    criar_tenant_public()