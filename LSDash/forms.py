from django.contrib.auth.forms import AuthenticationForm
from .models import UserModel
from django.core.exceptions import ValidationError

class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Atualizando campos para email em vez de username
        self.fields['username'].label = 'Email'  # O campo é chamado 'username' no AuthenticationForm
        self.fields['username'].widget.attrs.update({
            'maxlength': 100,
            'placeholder': 'E-mail'
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Password'
        })

    def clean_username(self):
        # Realiza a verificação do usuário por email
        email = self.cleaned_data.get('username')  # AuthenticationForm sempre usa 'username'
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            raise ValidationError("Usuário com este e-mail não foi encontrado.")
        
        if not user.is_active:
            raise ValidationError("Este usuário está inativo.")
        
        return email

    def clean_password(self):
        # Realiza a verificação da senha
        password = self.cleaned_data.get('password')
        email = self.cleaned_data.get('username')  # Aqui o campo é username, mas contém o email
        
        if email and password:
            try:
                user = UserModel.objects.get(email=email)
                if not user.check_password(password):
                    raise ValidationError("Senha incorreta.")
            except UserModel.DoesNotExist:
                pass  # Este erro já será capturado em clean_username
        
        return password