from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
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
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_master = models.BooleanField(default=False)  # Se é administrador dentro do tenant
    date_joined = models.DateTimeField(default=timezone.now)
    
    objects = UsuarioClienteManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']
    
    def __str__(self):
        return f"{self.nome} ({self.email})"