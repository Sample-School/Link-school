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