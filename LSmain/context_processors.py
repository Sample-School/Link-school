from django_tenants.utils import get_public_schema_name

def tenant_settings(request):
    """
    Context processor que adiciona configurações baseadas no tenant atual ao contexto.
    Isso torna as variáveis disponíveis em todos os templates.
    """
    tenant = request.tenant
    
    # Configurações específicas para o tenant
    if tenant.schema_name == get_public_schema_name():
        # Tenant público (Master)
        login_url = '/login/'
        home_url = '/'
        password_reset_url = '/password_reset/'
    else:
        # Tenant cliente
        login_url = '/clientelogin/'
        home_url = '/home/'
        password_reset_url = '/clientepassword_reset/'
    
    return {
        'tenant_login_url': login_url,
        'tenant_home_url': home_url,
        'tenant_password_reset_url': password_reset_url,
        'is_public_schema': tenant.schema_name == get_public_schema_name(),
    }