from django_tenants.utils import get_public_schema_name

def tenant_settings(request):
    """
    Context processor que disponibiliza configurações do tenant nos templates.
    Define URLs e flags baseadas no schema atual (público ou cliente).
    """
    tenant = request.tenant
    
    # Define URLs baseadas no tipo de tenant
    if tenant.schema_name == get_public_schema_name():
        # Schema público (master) - URLs padrão
        login_url = '/login/'
        home_url = '/'
        password_reset_url = '/password_reset/'
    else:
        # Schema de cliente - URLs específicas
        login_url = '/clientelogin/'
        home_url = '/home/'
        password_reset_url = '/clientepassword_reset/'
    
    return {
        'tenant_login_url': login_url,
        'tenant_home_url': home_url,
        'tenant_password_reset_url': password_reset_url,
        'is_public_schema': tenant.schema_name == get_public_schema_name(),
    }