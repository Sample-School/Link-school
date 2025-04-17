from django.contrib import admin
from .models import UserModel, Pagina, FamiliaPagina

@admin.register(UserModel)
class UserModelAdmin(admin.ModelAdmin):
    list_display = ('username', 'fullname', 'email', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'fullname')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')
    
    readonly_fields = ('date_joined',)
    ordering = ('-date_joined',)
    list_per_page = 20

    filter_horizontal = ('paginas',)  # Adiciona caixa com múltipla seleção para as páginas

    actions = ['activate_users', 'deactivate_users']

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
    activate_users.short_description = "Ativar usuários selecionados"

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_users.short_description = "Desativar usuários selecionados"

# Registra os modelos auxiliares também
@admin.register(Pagina)
class PaginaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'familia')
    search_fields = ('nome', 'codigo')
    list_filter = ('familia',)

@admin.register(FamiliaPagina)
class FamiliaPaginaAdmin(admin.ModelAdmin):
    list_display = ('nome_exibicao',)
    search_fields = ('nome_exibicao',)
