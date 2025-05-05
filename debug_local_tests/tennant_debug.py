"""
Script de diagnóstico para o Django Tenants
Coloque este arquivo na raiz do seu projeto Django e execute:
python tenant_debug.py
"""
import os
import django
import sys

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LSmain.settings')
django.setup()

# Importar modelos necessários
from django_tenants.utils import get_tenant_model, get_tenant_domain_model
from django_tenants.utils import schema_context, tenant_context

# Tenant e Domain models
TenantModel = get_tenant_model()
DomainModel = get_tenant_domain_model()

def test_domain_resolution(domain_name):
    """Teste se um domínio específico resolve para o tenant correto"""
    try:
        # Tenta buscar o domínio
        domain = DomainModel.objects.get(domain=domain_name)
        tenant = domain.tenant
        
        print(f"✅ Domínio '{domain_name}' encontrado!")
        print(f"   - Associado ao tenant: {tenant.nome} (schema: {tenant.schema_name})")
        
        # Testa se podemos acessar o contexto do tenant
        try:
            with tenant_context(tenant):
                print(f"   - Contexto do tenant acessado com sucesso")
        except Exception as e:
            print(f"   - ❌ Erro ao acessar o contexto do tenant: {e}")
        
        return True
    except DomainModel.DoesNotExist:
        print(f"❌ Domínio '{domain_name}' não encontrado no banco de dados!")
        
        # Lista todos os domínios disponíveis
        all_domains = DomainModel.objects.all()
        print("\nDomínios disponíveis:")
        for d in all_domains:
            print(f" - {d.domain} (Tenant: {d.tenant.nome})")
        
        return False
    except Exception as e:
        print(f"❌ Erro ao buscar o domínio '{domain_name}': {e}")
        return False

def show_all_tenants():
    """Mostra todos os tenants e seus domínios"""
    print("\n=== INFORMAÇÕES DE TODOS OS TENANTS ===")
    
    # Lista todos os tenants
    tenants = TenantModel.objects.all()
    for tenant in tenants:
        print(f"Tenant: {tenant.nome}")
        print(f"  Schema: {tenant.schema_name}")
        print(f"  É público: {'Sim' if tenant.schema_name == 'public' else 'Não'}")
        
        # Lista domínios associados
        domains = DomainModel.objects.filter(tenant=tenant)
        print(f"  Domínios ({domains.count()}):")
        for domain in domains:
            print(f"    - {domain.domain}")
    
    return len(tenants)

def check_middleware_order():
    """Verifica a ordem dos middlewares"""
    from django.conf import settings
    
    print("\n=== VERIFICAÇÃO DOS MIDDLEWARES ===")
    
    # Verifica se o TenantMainMiddleware está na primeira posição
    if settings.MIDDLEWARE[0] == 'django_tenants.middleware.main.TenantMainMiddleware':
        print("✅ TenantMainMiddleware está na primeira posição (correto)")
    else:
        print(f"❌ TenantMainMiddleware NÃO está na primeira posição!")
        print(f"   Primeiro middleware é: {settings.MIDDLEWARE[0]}")
    
    # Lista todos os middlewares
    print("\nOrdem dos middlewares:")
    for i, middleware in enumerate(settings.MIDDLEWARE, 1):
        print(f"{i}. {middleware}")

def main():
    print("=== DIAGNÓSTICO DO DJANGO TENANTS ===")
    
    # Verifica a configuração de middlewares
    check_middleware_order()
    
    # Mostra todos os tenants
    tenant_count = show_all_tenants()
    print(f"\nTotal de tenants: {tenant_count}")
    
    # Testa um domínio específico
    test_domain = "testejaum.localhost"
    print(f"\n=== TESTE DE RESOLUÇÃO DE DOMÍNIO: {test_domain} ===")
    test_domain_resolution(test_domain)
    
    # Teste também do domínio público
    test_domain = "localhost"
    print(f"\n=== TESTE DE RESOLUÇÃO DE DOMÍNIO: {test_domain} ===")
    test_domain_resolution(test_domain)

if __name__ == "__main__":
    main()