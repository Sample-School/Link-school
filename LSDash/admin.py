from django.contrib import admin
from .models import (
    UserModel,
    Pagina,
    FamiliaPagina,
    Cliente,
    Dominio,
    UsuarioMaster,
)


@admin.register(UserModel)
class UserModelAdmin(admin.ModelAdmin):
    list_display = ('username', 'fullname', 'email', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'fullname')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')
    readonly_fields = ('date_joined',)
    ordering = ('-date_joined',)
    list_per_page = 20
    filter_horizontal = ('paginas',)

    actions = ['activate_users', 'deactivate_users']

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
    activate_users.short_description = "Ativar usuários selecionados"

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_users.short_description = "Desativar usuários selecionados"


@admin.register(Pagina)
class PaginaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'familia')
    search_fields = ('nome', 'codigo')
    list_filter = ('familia',)


@admin.register(FamiliaPagina)
class FamiliaPaginaAdmin(admin.ModelAdmin):
    list_display = ('nome_exibicao',)
    search_fields = ('nome_exibicao',)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'responsavel', 'email_contato', 'qtd_usuarios', 'esta_ativo', 'criado_em')
    search_fields = ('nome', 'responsavel', 'email_contato')
    list_filter = ('criado_em', 'data_validade_assinatura')
    readonly_fields = ('criado_em', 'atualizado_em')
    date_hierarchy = 'criado_em'


@admin.register(Dominio)
class DominioAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    search_fields = ('domain',)
    list_filter = ('is_primary',)


@admin.register(UsuarioMaster)
class UsuarioMasterAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'cliente', 'is_active', 'is_staff', 'is_master', 'date_joined')
    search_fields = ('nome', 'email')
    list_filter = ('is_active', 'is_master', 'is_staff')
    readonly_fields = ('date_joined',)
