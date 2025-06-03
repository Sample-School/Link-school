from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

# Create your models here.
class UsuarioClienteManager(BaseUserManager):
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
        extra_fields.setdefault('is_master', True)

        return self.create_user(email, password, **extra_fields)


class UsuarioCliente(AbstractBaseUser, PermissionsMixin):
    """
    Usuário dentro de um tenant específico.
    Este modelo fica no schema do tenant.
    """
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_master = models.BooleanField(default=False)  # Se é administrador dentro do tenant
    date_joined = models.DateTimeField(default=timezone.now)
    foto = models.ImageField(upload_to='usuarios/', blank=True, null=True)


    objects = UsuarioClienteManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']
    
    def __str__(self):
        return f"{self.nome} ({self.email})"
    
    class Meta:
        verbose_name = 'Usuário Cliente'
        verbose_name_plural = 'Usuários Cliente'
    
    def set_password(self, raw_password):
        """
        Define a senha do usuário, convertendo-a para um hash utilizando
        o sistema de hash de senhas do Django.
        """
        self.password = make_password(raw_password)
        # Só use update_fields se o objeto já tiver um ID
        if self.pk:
            self.save(update_fields=['password'])
        # Caso contrário, não salve aqui - o save será chamado posteriormente
    
    def check_password(self, raw_password):
        """
        Verifica se a senha fornecida corresponde à senha armazenada.
        """
        return check_password(raw_password, self.password)
    
    @property
    def is_authenticated(self):
        """
        Sempre retorna True para usuários reais. Este é um requisito para
        usar o sistema de autenticação do Django.
        """
        return True
    
    @property
    def is_anonymous(self):
        """
        Sempre retorna False para usuários reais. Este é um requisito para
        usar o sistema de autenticação do Django.
        """
        return False
    
    def get_username(self):
        """
        Retorna o campo usado como identificador do usuário.
        """
        return self.email

class SessaoUsuarioCliente(models.Model):
    """Modelo para rastrear sessões ativas de usuários no contexto do cliente"""
    usuario = models.ForeignKey('UsuarioCliente', on_delete=models.CASCADE, related_name='sessoes')
    chave_sessao = models.CharField(max_length=40)
    data_inicio = models.DateTimeField(auto_now_add=True)
    ultima_atividade = models.DateTimeField(auto_now=True)
    endereco_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        unique_together = ('usuario', 'chave_sessao')
        verbose_name = 'Sessão de Usuário Cliente'
        verbose_name_plural = 'Sessões de Usuários Cliente'
    
    def __str__(self):
        return f"Sessão de {self.usuario.nome} - {self.chave_sessao[:8]}"


class ClienteSystemSettings(models.Model):
    imagem_home_1 = models.ImageField(upload_to='logos_clientes/', null=True, blank=True)
    system_primary_color = models.CharField(max_length=7, default="#3E3D3F")  # Cor padrão para Sair
    system_second_color = models.CharField(max_length=7, default="#575758")  # Cor padrão para Geral
    tempo_maximo_inatividade = models.IntegerField(default=30, help_text="Tempo máximo de inatividade em minutos")
    
    @classmethod
    def obter_configuracao(cls):
        """Retorna a configuração atual ou cria uma nova se não existir"""
        configuracao, created = cls.objects.get_or_create(id=1)
        return configuracao
    
    def __str__(self):
        return "Configurações do Sistema"


class Prova(models.Model):
    TIPO_PROVA_CHOICES = [
        ('avaliacao', 'Avaliação'),
        ('simulado', 'Simulado'),
        ('teste', 'Teste'),
        ('trabalho', 'Trabalho'),
        ('prova_bimestral', 'Prova Bimestral'),
        ('prova_final', 'Prova Final'),
    ]
    
    titulo = models.CharField(max_length=200, verbose_name="Título da Prova")
    materia = models.CharField(max_length=100, verbose_name="Matéria")
    tipo_prova = models.CharField(max_length=20, choices=TIPO_PROVA_CHOICES, verbose_name="Tipo de Prova")
    criado_por = models.ForeignKey('UsuarioCliente', on_delete=models.CASCADE, related_name='provas_criadas')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    # Configurações de formatação (para futuras funcionalidades)
    fonte_padrao = models.CharField(max_length=50, default="Arial", verbose_name="Fonte Padrão")
    tamanho_fonte = models.IntegerField(default=12, verbose_name="Tamanho da Fonte")
    
    def __str__(self):
        return f"{self.titulo} - {self.materia}"
    
    class Meta:
        verbose_name = 'Prova'
        verbose_name_plural = 'Provas'


class QuestaoProva(models.Model):
    """Relaciona questões à prova com ordem específica"""
    prova = models.ForeignKey(Prova, on_delete=models.CASCADE, related_name='questoes_prova')
    questao_id = models.IntegerField(verbose_name="ID da Questão do Dashboard")
    questao_dados = models.JSONField(verbose_name="Dados da Questão")  # Cache dos dados da questão
    ordem = models.IntegerField(verbose_name="Ordem na Prova")
    
    # Configurações específicas desta questão na prova
    texto_destacado = models.JSONField(default=list, blank=True)  # Lista de textos para destacar
    fonte_customizada = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['ordem']
        unique_together = ('prova', 'ordem')
    
    def __str__(self):
        return f"Questão {self.ordem} - Prova {self.prova.titulo}"