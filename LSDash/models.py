# Models do sistema de ensino multi-tenant
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django_tenants.models import TenantMixin, DomainMixin


# Modelos de sistema de páginas e permissões
class FamiliaPagina(models.Model):
    """Agrupa páginas relacionadas do sistema para organização de permissões"""
    nome_exibicao = models.CharField(max_length=100)
    descricao = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.nome_exibicao


class Pagina(models.Model):
    """Representa uma página/funcionalidade do sistema"""
    codigo = models.CharField(max_length=50, unique=True)
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(null=True, blank=True)
    familia = models.ForeignKey(FamiliaPagina, on_delete=models.CASCADE, related_name='paginas')

    def __str__(self):
        return f"{self.nome} ({self.codigo})"


# Sistema de usuários personalizados
class UserManager(BaseUserManager):
    """Manager customizado para o modelo de usuário"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O campo E-mail é obrigatório.')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('O superusuário deve ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('O superusuário deve ter is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class UserModel(AbstractBaseUser, PermissionsMixin):
    """Modelo de usuário customizado para o sistema"""
    user_id = models.AutoField(primary_key=True)
    user_img = models.ImageField(null=True, blank=True)
    username = models.CharField(max_length=30, null=False)
    fullname = models.CharField(max_length=100, null=False)
    email = models.EmailField(unique=True, null=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    observacoes = models.TextField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    paginas = models.ManyToManyField('Pagina', related_name='usuarios', blank=True)
    
    # Relacionamentos necessários para o sistema de permissões do Django
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='user_model_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='user_model_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
    def obter_paginas_por_familia(self):
        """Organiza as páginas do usuário por família para facilitar a navegação"""
        paginas_por_familia = {}
        for pagina in self.paginas.select_related('familia').all():
            familia_nome = pagina.familia.nome_exibicao
            if familia_nome not in paginas_por_familia:
                paginas_por_familia[familia_nome] = []
            paginas_por_familia[familia_nome].append(pagina)
        return paginas_por_familia


# Sistema multi-tenant (clientes)
class ClienteManager(models.Manager):
    """Manager para facilitar a criação de clientes com usuário master"""
    def create_cliente_with_master(self, nome, email_master, password_master, **kwargs):
        """Cria um cliente e seu usuário master simultaneamente"""
        cliente = self.create(nome=nome, **kwargs)
        
        # Criar usuário master
        usuario_master = UsuarioMaster.objects.create_user(
            cliente=cliente,
            email=email_master,
            password=password_master,
            is_master=True
        )
        
        # Atualizar referência no cliente
        cliente.usuario_master = usuario_master
        cliente.save(update_fields=['usuario_master'])
        
        return cliente


class Cliente(TenantMixin):
    """Modelo de cliente/tenant do sistema multi-tenant"""
    nome = models.CharField(max_length=100, unique=True)
    cor_primaria = models.CharField(max_length=7, default="#000000")
    cor_secundaria = models.CharField(max_length=7, default="#FFFFFF")
    data_inicio_assinatura = models.DateField()
    data_validade_assinatura = models.DateField()
    observacoes = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos_clientes/', blank=True, null=True)
    qtd_usuarios = models.IntegerField(default=5)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    # Referência ao usuário master
    usuario_master = models.OneToOneField(
        'UsuarioMaster', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='cliente_administrado'
    )
    
    auto_create_schema = True
    objects = ClienteManager()
    
    def __str__(self):
        return self.nome
    
    def esta_ativo(self):
        """Verifica se a assinatura do cliente está válida"""
        return timezone.now().date() <= self.data_validade_assinatura


class Dominio(DomainMixin):
    """Modelo de domínio para o sistema multi-tenant"""
    pass


class UsuarioMasterManager(BaseUserManager):
    """Manager para usuários master que gerenciam tenants"""
    def create_user(self, email, password, cliente, **extra_fields):
        if not email:
            raise ValueError('O campo E-mail é obrigatório.')

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            cliente=cliente,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class UsuarioMaster(AbstractBaseUser, PermissionsMixin):
    """Usuário master que gerencia um tenant/cliente no schema compartilhado"""
    id = models.AutoField(primary_key=True)
    
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_master = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    
    # Relacionamentos para sistema de permissões
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='usuario_master_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='usuario_master_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )
    
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE,
        related_name='usuarios_master'
    )
    
    objects = UsuarioMasterManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['cliente']
    
    def __str__(self):
        return f"{self.email} ({self.cliente.nome})"


# Sistema educacional
class GrupoEnsino(models.Model):
    """Agrupa anos escolares por nível de ensino"""
    nome = models.CharField(max_length=50)  # Ex: "Fundamental 1", "Fundamental 2", "Ensino Médio"
    
    def __str__(self):
        return self.nome


class AnoEscolar(models.Model):
    """Representa um ano/série escolar específico"""
    grupo_ensino = models.ForeignKey(GrupoEnsino, on_delete=models.CASCADE, related_name='anos')
    nome = models.CharField(max_length=50)  # Ex: "1º Ano", "2º Ano"
    ordem = models.IntegerField(default=0)  # Para ordenação correta
    
    class Meta:
        ordering = ['grupo_ensino', 'ordem']
    
    def __str__(self):
        return f"{self.nome} - {self.grupo_ensino.nome}"


class Materia(models.Model):
    """Disciplinas/matérias escolares"""
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome


# Sistema de questões e avaliações
class Questao(models.Model):
    """Questões para avaliações e exercícios"""
    TIPO_CHOICES = [
        ('aberta', 'Questão Aberta'),
        ('multipla', 'Múltipla Escolha'),
        ('vf', 'Verdadeiro ou Falso'),
    ]
    
    titulo = models.CharField(max_length=255, verbose_name="Enunciado")
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='questoes')
    ano_escolar = models.ForeignKey(AnoEscolar, on_delete=models.CASCADE, related_name='questoes')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    criado_por = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='questoes')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.titulo[:50]}... ({self.get_tipo_display()})"


class ImagemQuestao(models.Model):
    """Imagens anexadas às questões"""
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE, related_name='imagens')
    imagem = models.ImageField(upload_to='imagens_questoes/')
    legenda = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"Imagem para questão {self.questao.id}"


class AlternativaMultiplaEscolha(models.Model):
    """Alternativas para questões de múltipla escolha"""
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE, related_name='alternativas')
    texto = models.CharField(max_length=255)
    correta = models.BooleanField(default=False)
    ordem = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['ordem']
    
    def __str__(self):
        return f"{self.texto[:30]}... {'(Correta)' if self.correta else ''}"


class FraseVerdadeiroFalso(models.Model):
    """Frases para questões de verdadeiro ou falso"""
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE, related_name='frases_vf')
    texto = models.CharField(max_length=255)
    verdadeira = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['ordem']
    
    def __str__(self):
        return f"{self.texto[:30]}... {'(V)' if self.verdadeira else '(F)'}"


# Configurações e sistema
class ConfiguracaoSistema(models.Model):
    """Configurações globais do sistema"""
    imagem_home_1 = models.ImageField(upload_to='imagens_sistema/home/', null=True, blank=True)
    imagem_home_2 = models.ImageField(upload_to='imagens_sistema/home/', null=True, blank=True)
    observacoes = models.TextField(blank=True, null=True)
    tempo_maximo_inatividade = models.IntegerField(
        default=30, 
        help_text="Tempo máximo de inatividade em minutos"
    )
    
    @classmethod
    def obter_configuracao(cls):
        """Retorna a configuração atual ou cria uma nova se não existir"""
        configuracao, created = cls.objects.get_or_create(id=1)
        return configuracao
    
    def __str__(self):
        return "Configurações do Sistema"


class SessaoUsuario(models.Model):
    """Controle de sessões ativas dos usuários"""
    usuario = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='sessoes')
    chave_sessao = models.CharField(max_length=40)
    data_inicio = models.DateTimeField(auto_now_add=True)
    ultima_atividade = models.DateTimeField(auto_now=True)
    endereco_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        unique_together = ('usuario', 'chave_sessao')
    
    def __str__(self):
        return f"Sessão de {self.usuario.username} - {self.chave_sessao[:8]}"