
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model


#imports locais
from .models import UsuarioCliente

class UserLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'placeholder': 'E-mail',
        'class': 'form-control'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Senha',
        'class': 'form-control'
    }))
    
    def __init__(self, *args, **kwargs):
        # Extract request from kwargs if it exists
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            # É CRUCIAL passar o objeto request aqui!
            self.user = authenticate(request=self.request, username=email, password=password)
            if self.user is None:
                raise ValidationError("E-mail ou senha incorretos.")
            if not self.user.is_active:
                raise ValidationError("Esta conta está inativa.")
        return cleaned_data

    def get_user(self):
        return self.user

class NewResetPasswordForm(SetPasswordForm):
    """
    Formulário personalizado para redefinição de senha que funciona com o modelo UsuarioCliente
    """
    new_password1 = forms.CharField(
        label="Nova senha",
        widget=forms.PasswordInput(attrs={
            'class': 'password-input',
            'placeholder': 'Digite sua nova senha',
            'id': 'id_new_password1'
        })
    )
    
    new_password2 = forms.CharField(
        label="Confirme a nova senha",
        widget=forms.PasswordInput(attrs={
            'class': 'password-input',
            'placeholder': 'Confirme sua nova senha',
            'id': 'id_new_password2'
        })
    )
    
    def __init__(self, user=None, *args, **kwargs):
        # Verificar se o usuário é do tipo correto
        from LSCliente.models import UsuarioCliente
        
        if user is not None and not isinstance(user, UsuarioCliente):
            # Tente obter o usuário correto se o ID for passado
            try:
                if hasattr(user, 'pk'):
                    user_id = user.pk
                    user = UsuarioCliente.objects.get(pk=user_id)
                elif isinstance(user, int) or (isinstance(user, str) and user.isdigit()):
                    user = UsuarioCliente.objects.get(pk=user)
                else:
                    raise ValueError("Este formulário deve ser usado com um objeto UsuarioCliente")
            except UsuarioCliente.DoesNotExist:
                raise ValueError("Este formulário deve ser usado com um objeto UsuarioCliente")
            
        self.user = user
        super(SetPasswordForm, self).__init__(*args, **kwargs)
        
    def save(self, commit=True):
        # Defina a senha para o usuário UsuarioCliente
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user

class CustomPasswordResetForm(PasswordResetForm):
    """
    Formulário personalizado para solicitação de redefinição de senha
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Seu endereço de e-mail',
            'class': 'email-input'
        })
    )
    
    def __init__(self, *args, **kwargs):
        # Extrair o request dos kwargs
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_email(self):
        """
        Valida que o email fornecido está associado a uma conta de usuário 
        e mostra mensagens de erro mais claras
        """
        email = self.cleaned_data.get('email')
        if email:
            # Debug info
            print(f"[DEBUG] Verificando email: {email}")
            print(f"[DEBUG] Tenant atual: {self.request.tenant.schema_name if hasattr(self.request, 'tenant') else 'Desconhecido'}")
            
            # No contexto de um tenant, sempre use UsuarioCliente
            if hasattr(self.request, 'tenant') and self.request.tenant.schema_name != 'public':
                active_users = UsuarioCliente.objects.filter(email__iexact=email, is_active=True)
                print(f"[DEBUG] Usuários encontrados no tenant {self.request.tenant.schema_name}: {active_users.count()}")
            else:
                # No schema público, use o modelo UserModel padrão
                model = get_user_model()
                active_users = model.objects.filter(email__iexact=email, is_active=True)
                print(f"[DEBUG] Usuários encontrados no schema público: {active_users.count()}")
            
            if not active_users.exists():
                raise ValidationError("Não existe um usuário ativo com o e-mail fornecido.")
        return email

    def get_users(self, email):
        """
        Este método é chamado pelo PasswordResetForm para obter uma QuerySet
        dos usuários elegíveis para redefinição de senha.
        """
        print(f"[DEBUG] get_users chamado para email: {email}")
        
        if hasattr(self, 'request') and self.request and hasattr(self.request, 'tenant') and self.request.tenant.schema_name != 'public':
            # Em um tenant, sempre use UsuarioCliente
            active_users = UsuarioCliente.objects.filter(email__iexact=email, is_active=True)
            print(f"[DEBUG] Buscando UsuarioCliente no tenant {self.request.tenant.schema_name}, encontrados: {active_users.count()}")
            return active_users
        else:
            # No schema público, use o modelo UserModel padrão
            UserModel = get_user_model()
            active_users = UserModel.objects.filter(email__iexact=email, is_active=True)
            print(f"[DEBUG] Buscando UserModel no schema público, encontrados: {active_users.count()}")
            return active_users