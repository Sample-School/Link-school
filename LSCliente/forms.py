# Forms para autenticação e gerenciamento do sistema cliente
from django.contrib.auth.forms import SetPasswordForm, PasswordResetForm
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django import forms

# Models locais
from .models import UsuarioCliente, ClienteSystemSettings


class UserLoginForm(forms.Form):
    """Form de login customizado para o sistema cliente"""
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'placeholder': 'E-mail',
        'class': 'form-control'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Senha',
        'class': 'form-control'
    }))
    
    def __init__(self, *args, **kwargs):
        # Preciso do request para o contexto de autenticação
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            # Request é essencial aqui para o tenant funcionar
            self.user = authenticate(request=self.request, username=email, password=password)
            if self.user is None:
                raise ValidationError("E-mail ou senha incorretos.")
            if not self.user.is_active:
                raise ValidationError("Esta conta está inativa.")
        return cleaned_data

    def get_user(self):
        return self.user


class NewResetPasswordForm(SetPasswordForm):
    """Form para redefinir senha - funciona especificamente com UsuarioCliente"""
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
        # Garantir que estamos trabalhando com UsuarioCliente
        from LSCliente.models import UsuarioCliente
        
        if user is not None and not isinstance(user, UsuarioCliente):
            # Tentar converter se veio ID ou objeto errado
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
        # Salvar a nova senha no UsuarioCliente
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class CustomPasswordResetForm(PasswordResetForm):
    """Form personalizado para solicitar reset de senha"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Seu endereço de e-mail',
            'class': 'email-input'
        })
    )
    
    def __init__(self, *args, **kwargs):
        # Request necessário para trabalhar com tenants
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_email(self):
        """Valida se o email existe e está ativo no sistema"""
        email = self.cleaned_data.get('email')
        if email:
            # Debug para acompanhar o processo
            print(f"[DEBUG] Verificando email: {email}")
            print(f"[DEBUG] Tenant atual: {self.request.tenant.schema_name if hasattr(self.request, 'tenant') else 'Desconhecido'}")
            
            # Dentro de um tenant, sempre usar UsuarioCliente
            if hasattr(self.request, 'tenant') and self.request.tenant.schema_name != 'public':
                active_users = UsuarioCliente.objects.filter(email__iexact=email, is_active=True)
                print(f"[DEBUG] Usuários encontrados no tenant {self.request.tenant.schema_name}: {active_users.count()}")
            else:
                # No schema público, usar o modelo padrão
                model = get_user_model()
                active_users = model.objects.filter(email__iexact=email, is_active=True)
                print(f"[DEBUG] Usuários encontrados no schema público: {active_users.count()}")
            
            if not active_users.exists():
                raise ValidationError("Não existe um usuário ativo com o e-mail fornecido.")
        return email

    def get_users(self, email):
        """Retorna os usuários elegíveis para reset de senha"""
        print(f"[DEBUG] get_users chamado para email: {email}")
        
        if hasattr(self, 'request') and self.request and hasattr(self.request, 'tenant') and self.request.tenant.schema_name != 'public':
            # Em tenant, usar UsuarioCliente
            active_users = UsuarioCliente.objects.filter(email__iexact=email, is_active=True)
            print(f"[DEBUG] Buscando UsuarioCliente no tenant {self.request.tenant.schema_name}, encontrados: {active_users.count()}")
            return active_users
        else:
            # No público, usar modelo padrão
            UserModel = get_user_model()
            active_users = UserModel.objects.filter(email__iexact=email, is_active=True)
            print(f"[DEBUG] Buscando UserModel no schema público, encontrados: {active_users.count()}")
            return active_users


class UsuarioClienteForm(forms.ModelForm):
    """Form para criar/editar usuários do sistema cliente"""
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Senha'
    )
    password_confirm = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirmar Senha'
    )
    
    class Meta:
        model = UsuarioCliente
        fields = ['nome', 'email', 'password', 'is_active', 'foto']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.RadioSelect(choices=[(True, 'Ativo'), (False, 'Inativo')]),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nome': 'Nome',
            'email': 'Email',
            'is_active': 'Status',
            'foto': 'Foto',
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        # Para usuário novo, senha é obrigatória
        if not self.instance.pk and not password:
            self.add_error('password', 'A senha é obrigatória para novos usuários.')

        # Se preencheu senha, tem que confirmar
        if password and password != password_confirm:
            self.add_error('password_confirm', 'As senhas não coincidem.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')

        # Só alterar senha se foi informada
        if password:
            user.password = make_password(password)

        # Manter consistência - usuário cliente não tem acesso admin
        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()
        return user


class ClienteSystemSettingsForm(forms.ModelForm):
    """Form para configurações gerais do sistema cliente"""
    class Meta:
        model = ClienteSystemSettings
        fields = ['imagem_home_1', 'system_primary_color', 'system_second_color', 'tempo_maximo_inatividade']
        widgets = {
            'system_primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'system_second_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'tempo_maximo_inatividade': forms.NumberInput(attrs={'min': '1', 'max': '1440', 'class': 'form-control'}),
        }