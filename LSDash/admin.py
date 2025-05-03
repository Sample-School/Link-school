from django.contrib import admin
from .models import (
    FamiliaPagina, Pagina, UserModel, Cliente, Dominio,
    UsuarioMaster, GrupoEnsino, AnoEscolar, Materia,
    Questao, ImagemQuestao, AlternativaMultiplaEscolha, FraseVerdadeiroFalso
)
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


# ========== Inline Models ==========
class ImagemQuestaoInline(admin.TabularInline):
    model = ImagemQuestao
    extra = 1


class AlternativaMultiplaEscolhaInline(admin.TabularInline):
    model = AlternativaMultiplaEscolha
    extra = 2


class FraseVerdadeiroFalsoInline(admin.TabularInline):
    model = FraseVerdadeiroFalso
    extra = 2


# ========== ModelAdmin Configs ==========

@admin.register(FamiliaPagina)
class FamiliaPaginaAdmin(admin.ModelAdmin):
    list_display = ('nome_exibicao', 'descricao')
    search_fields = ('nome_exibicao',)


@admin.register(Pagina)
class PaginaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'familia')
    list_filter = ('familia',)
    search_fields = ('nome', 'codigo')


@admin.register(UserModel)
class CustomUserAdmin(BaseUserAdmin):
    model = UserModel
    list_display = ('email', 'username', 'fullname', 'is_active', 'is_staff')
    list_filter = ('is_staff', 'is_active', 'paginas')
    search_fields = ('email', 'username', 'fullname')
    ordering = ('email',)
    filter_horizontal = ('paginas', 'groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informações Pessoais', {'fields': ('username', 'fullname', 'user_img', 'observacoes')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Relacionamentos', {'fields': ('paginas',)}),
        ('Datas', {'fields': ('date_joined',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data_inicio_assinatura', 'data_validade_assinatura', 'esta_ativo')
    search_fields = ('nome', )
    list_filter = ('data_validade_assinatura',)
    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(Dominio)
class DominioAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    search_fields = ('domain',)


@admin.register(UsuarioMaster)
class UsuarioMasterAdmin(admin.ModelAdmin):
    list_display = ( 'email', 'cliente', 'is_master', 'is_active')
    search_fields = ( 'email', 'cliente__nome')
    list_filter = ('is_master', 'is_active')


@admin.register(GrupoEnsino)
class GrupoEnsinoAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)


@admin.register(AnoEscolar)
class AnoEscolarAdmin(admin.ModelAdmin):
    list_display = ('nome', 'grupo_ensino', 'ordem')
    list_filter = ('grupo_ensino',)
    ordering = ('grupo_ensino', 'ordem')
    search_fields = ('nome', 'grupo_ensino__nome')  # Necessário para autocomplete


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)  # Necessário para autocomplete


@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'materia', 'ano_escolar', 'tipo', 'criado_por', 'data_criacao')
    list_filter = ('materia', 'ano_escolar', 'tipo')
    search_fields = ('titulo', 'materia__nome')
    inlines = [ImagemQuestaoInline, AlternativaMultiplaEscolhaInline, FraseVerdadeiroFalsoInline]
    autocomplete_fields = ('materia', 'ano_escolar', 'criado_por')


# As inlines estão ligadas à Questao, então não é necessário registrar ImagemQuestao, AlternativaMultiplaEscolha e FraseVerdadeiroFalso separadamente
