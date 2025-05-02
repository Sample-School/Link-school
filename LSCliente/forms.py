
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import authenticate

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
            self.user = authenticate(username=email, password=password)
            if self.user is None:
                raise ValidationError("E-mail ou senha incorretos.")
            if not self.user.is_active:
                raise ValidationError("Esta conta está inativa.")
        return cleaned_data

    def get_user(self):
        return self.user

class NewResetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'placeholder': 'Nova senha',
            'class': 'password-input'
        })
        self.fields['new_password2'].widget.attrs.update({
            'placeholder': 'Confirme a nova senha',
            'class': 'password-input'
        })

class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Seu endereço de e-mail',
            'class': 'email-input'
        })