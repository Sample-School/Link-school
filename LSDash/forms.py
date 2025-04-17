from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django import forms

#imports locais
from .models import UserModel, Pagina

from django.contrib.auth.forms import PasswordResetForm

class UserLoginForm(AuthenticationForm):
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

class NewResetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.fields['new_password1'].help_text = mark_safe("<h1>tenho tdah</h1>")


class CollabManageForm(forms.ModelForm):
    tipo_usuario = forms.ChoiceField(
        choices=[('colaborador', 'Colaborador'), ('adm', 'Administrador')],
        widget=forms.RadioSelect,
        required=True,
        error_messages={
            'required': 'Por favor, selecione o tipo de usuário.',
        },
    )

    status = forms.ChoiceField(
        choices=[('ativo', 'Ativo'), ('inativo', 'Inativo')],
        widget=forms.RadioSelect(attrs={'id': 'status-field'}),
        required=True,
        error_messages={
            'required': 'Por favor, selecione o status.',
        },
    )

    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,  # Permite que a senha não seja obrigatória para atualização
        label="Senha",
        error_messages={
            'required': 'Por favor, insira uma senha.',
        },
    )

    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 40}),
        required=False,
        label="Observações",
        error_messages={
            'required': 'Este campo é obrigatório.',
        },
    )

    paginas = forms.ModelMultipleChoiceField(
        queryset=Pagina.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Páginas",
        help_text="Selecione uma ou mais páginas"
    )

    class Meta:
        model = UserModel
        fields = ['username', 'fullname', 'email', 'tipo_usuario', 'status', 'observacoes', 'paginas']
        error_messages = {
            'username': {
                'required': 'O nome de usuário é obrigatório.',
                'max_length': 'O nome de usuário não pode ter mais de 150 caracteres.',
            },
            'email': {
                'required': 'O email é obrigatório.',
                'invalid': 'Por favor, insira um email válido.',
            },
        }

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)

        # Garantir que o queryset de páginas está sempre atualizado
        self.fields['paginas'].queryset = Pagina.objects.all()

        if self.instance:
            # Definir valores iniciais com base no instance
            self.fields['tipo_usuario'].initial = 'adm' if self.instance.is_staff else 'colaborador'
            self.fields['status'].initial = 'ativo' if self.instance.is_active else 'inativo'
            self.fields['observacoes'].initial = self.instance.observacoes

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if UserModel.objects.filter(username=username).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("Este nome de usuário já está em uso. Escolha outro.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if UserModel.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("Este email já está cadastrado. Por favor, use outro.")
        return email

    def clean_tipo_usuario(self):
        tipo_usuario = self.cleaned_data.get('tipo_usuario')
        if tipo_usuario == 'adm':
            self.instance.is_staff = True
            self.instance.is_superuser = True
        else:
            self.instance.is_staff = False
            self.instance.is_superuser = False
        return tipo_usuario

    def clean_status(self):
        status = self.cleaned_data.get('status')
        self.instance.is_active = (status == 'ativo')
        return status

    def save(self, commit=True):
        # Salva o usuário, incluindo os grupos de acesso
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        if password:  # Só define a senha se o campo estiver preenchido
            user.set_password(password)

        if commit:
            user.save()
            self.save_m2m()  # Salva as relações many-to-many, incluindo páginas
        return user