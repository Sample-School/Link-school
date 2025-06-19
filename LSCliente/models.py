from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone


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
    # Modelo customizado de usuário para trabalhar com multi-tenancy
    # Cada tenant tem seus próprios usuários no schema específico
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_master = models.BooleanField(default=False)  # Admin do tenant específico
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
        # Converte a senha para hash usando o sistema do Django
        self.password = make_password(raw_password)
        # Só salva se o objeto já existe no banco
        if self.pk:
            self.save(update_fields=['password'])
    
    def check_password(self, raw_password):
        # Verifica se a senha informada bate com a armazenada
        return check_password(raw_password, self.password)
    
    @property
    def is_authenticated(self):
        # Sempre True para usuários válidos - requisito do Django auth
        return True
    
    @property
    def is_anonymous(self):
        # Sempre False para usuários válidos - requisito do Django auth
        return False
    
    def get_username(self):
        # Retorna o email como identificador único
        return self.email


class SessaoUsuarioCliente(models.Model):
    # Controla as sessões ativas dos usuários dentro do tenant
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
    # Configurações globais do sistema para cada tenant
    imagem_home_1 = models.ImageField(upload_to='logos_clientes/', null=True, blank=True)
    system_primary_color = models.CharField(max_length=7, default="#3E3D3F")
    system_second_color = models.CharField(max_length=7, default="#575758")
    tempo_maximo_inatividade = models.IntegerField(default=30, help_text="Tempo máximo de inatividade em minutos")
    
    @classmethod
    def obter_configuracao(cls):
        # Singleton pattern - sempre retorna a mesma instância de configuração
        configuracao, created = cls.objects.get_or_create(id=1)
        return configuracao
    
    def __str__(self):
        return "Configurações do Sistema"


class QuestaoProva(models.Model):
    FONTE_IMAGEM_CHOICES = [
        ('estatica', 'Imagem Estática'),
        ('dalle', 'Gerada por DALL-E'),
        ('upload', 'Upload do Usuário'),
    ]
    
    prova = models.ForeignKey('Prova', on_delete=models.CASCADE, related_name='questoes_prova')
    questao_id = models.CharField(max_length=100)  # ID vindo do dashboard
    questao_dados = models.JSONField()  # Todos os dados da questão em JSON
    ordem = models.PositiveIntegerField()
    acessibilidade_questao = models.IntegerField(default=1, choices=[(1, 'Grau 1'), (2, 'Grau 2'), (3, 'Grau 3')])
    
    # Campos para integração com DALL-E
    imagem_gerada = models.ImageField(upload_to='questoes/dalle/', blank=True, null=True)
    fonte_imagem = models.CharField(max_length=20, choices=FONTE_IMAGEM_CHOICES, default='estatica')
    prompt_dalle = models.TextField(blank=True, null=True)  # Guarda o prompt usado na geração
    data_geracao_imagem = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['ordem']
        unique_together = ['prova', 'ordem']
    
    def get_imagem_url(self):
        # Retorna a URL correta da imagem baseada na fonte configurada
        if self.fonte_imagem == 'dalle' and self.imagem_gerada:
            return self.imagem_gerada.url
        elif self.fonte_imagem == 'estatica':
            # Imagens estáticas ficam no diretório static
            return f"/static/LSCliente/img/questions/question_{self.questao_id}.png"
        elif self.fonte_imagem == 'upload' and self.imagem_gerada:
            return self.imagem_gerada.url
        return None
    
    def precisa_gerar_imagem(self):
        # Questões de acessibilidade grau 3 precisam de imagem gerada
        return (self.acessibilidade_questao == 3 and 
                self.fonte_imagem == 'dalle' and 
                not self.imagem_gerada)


class Prova(models.Model):
    TIPO_PROVA_CHOICES = [
        ('av1', 'Primeira Avaliação'),
        ('av2', 'Segunda Avaliação'),
        ('recuperacao', 'Recuperação'),
        ('final', 'Prova Final'),
    ]
    
    titulo = models.CharField(max_length=200)
    materia = models.CharField(max_length=100)
    tipo_prova = models.CharField(max_length=20, choices=TIPO_PROVA_CHOICES)
    acessibilidade_prova = models.IntegerField(default=1, choices=[(1, 'Grau 1'), (2, 'Grau 2'), (3, 'Grau 3')])
    criado_por = models.ForeignKey(UsuarioCliente, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    # Controle de geração de imagens via DALL-E
    imagens_geradas = models.BooleanField(default=False)
    data_geracao_imagens = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.titulo} - {self.materia}"
    
    def get_questoes_com_imagem(self):
        # Filtra questões que precisam de imagem (acessibilidade grau 3)
        return self.questoes_prova.filter(acessibilidade_questao=3)
    
    def todas_imagens_geradas(self):
        # Verifica se todas as imagens necessárias já foram processadas
        questoes_com_imagem = self.get_questoes_com_imagem()
        if not questoes_com_imagem.exists():
            return True
        return not questoes_com_imagem.filter(imagem_gerada__isnull=True).exists()