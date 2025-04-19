from django_tenants.middleware import TenantMainMiddleware

class SelectiveTenantMiddleware(TenantMainMiddleware):
    def process_request(self, request):
        # Lista de domínios que devem ignorar o sistema de tenants
        public_domains = ['127.0.0.1', 'localhost', 'sampletext.com']
        
        # Se o domínio estiver na lista de públicos, não processe como tenant
        if request.get_host().split(':')[0] in public_domains:
            return None
            
        # Caso contrário, use o processamento padrão de tenants
        return super().process_request(request)