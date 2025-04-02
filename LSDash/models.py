from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
# Create your models here.
class FamiliaPagina(models.Model):
    nome_exibicao = models.CharField(max_length=100)  # Nome exibido da família de páginas
    descricao = models.TextField(null=True, blank=True)  # Descrição da família (opcional)

    def __str__(self):
        return self.nome_exibicao

# Modelo para representar uma Página
class Pagina(models.Model):
    codigo = models.CharField(max_length=50, unique=True)  # Código único da página
    nome = models.CharField(max_length=100, unique=True)  # Nome da página
    descricao = models.TextField(null=True, blank=True)  # Descrição da página
    familia = models.ForeignKey(FamiliaPagina, on_delete=models.CASCADE, related_name='paginas')  # Relacionamento com a família de páginas

    def __str__(self):
        return f"{self.nome} ({self.codigo})"

class UserManager(BaseUserManager):
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


# Modelo Customizado para o Usuário
class UserModel(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=30, null=False)
    fullname = models.CharField(max_length=100, null=False)
    email = models.EmailField(unique=True, null=False)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    observacoes = models.TextField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'  # Alterado para email
    REQUIRED_FIELDS = ['username']  # Username agora é campo obrigatório, não mais o email

    def __str__(self):
        return self.email
