# Forms do sistema de ensino
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, PasswordResetForm
from django.core.exceptions import ValidationError
from django import forms

# Importações locais
from .models import (
    UserModel, Pagina, Cliente, GrupoEnsino, AnoEscolar, Materia, 
    Questao, ImagemQuestao, AlternativaMultiplaEscolha, 
    FraseVerdadeiroFalso, ConfiguracaoSistema
)


class UserLoginForm(AuthenticationForm):
    """Form customizado para login com validação por email"""
    
    def clean_username(self):
        """Valida se o usuário existe e está ativo"""
        email = self.cleaned_data.get('username')  # AuthenticationForm usa 'username'
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            raise ValidationError("Usuário com este e-mail não foi encontrado.")
        
        if not user.is_active:
            raise ValidationError("Este usuário está inativo.")
        
        return email

    def clean_password(self):
        """Valida a senha do usuário"""
        password = self.cleaned_data.get('password')
        email = self.cleaned_data.get('username')
        
        if email and password:
            try:
                user = UserModel.objects.get(email=email)
                if not user.check_password(password):
                    raise ValidationError("Senha incorreta.")
            except UserModel.DoesNotExist:
                pass  # Erro já capturado em clean_username
        
        return password


class NewResetPasswordForm(SetPasswordForm):
    """Form para redefinição de senha com estilos customizados"""
    
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
    """Form customizado para solicitação de reset de senha"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Seu endereço de e-mail',
            'class': 'email-input'
        })


class CollabManageForm(forms.ModelForm):
    """Form para gerenciamento de colaboradores do sistema"""
    
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
        required=False,  # Não obrigatório para edição
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
    
    user_img = forms.ImageField(
        required=False,
        label="Imagem do Usuário",
        widget=forms.FileInput(attrs={'class': 'form-control-file'}),
        help_text="Upload de uma imagem para o perfil do usuário"
    )

    class Meta:
        model = UserModel
        fields = ['username', 'fullname', 'email', 'tipo_usuario', 'status', 'observacoes', 'paginas', 'user_img']
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

        # Garantir queryset atualizado de páginas
        self.fields['paginas'].queryset = Pagina.objects.all()

        if self.instance:
            # Definir valores iniciais baseados na instância
            self.fields['tipo_usuario'].initial = 'adm' if self.instance.is_staff else 'colaborador'
            self.fields['status'].initial = 'ativo' if self.instance.is_active else 'inativo'
            self.fields['observacoes'].initial = self.instance.observacoes

    def clean_username(self):
        """Valida se o username não está em uso"""
        username = self.cleaned_data.get('username')
        if UserModel.objects.filter(username=username).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("Este nome de usuário já está em uso. Escolha outro.")
        return username

    def clean_email(self):
        """Valida se o email não está em uso"""
        email = self.cleaned_data.get('email')
        if UserModel.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("Este email já está cadastrado. Por favor, use outro.")
        return email

    def clean_tipo_usuario(self):
        """Define permissões baseadas no tipo de usuário"""
        tipo_usuario = self.cleaned_data.get('tipo_usuario')
        if tipo_usuario == 'adm':
            self.instance.is_staff = True
            self.instance.is_superuser = True
        else:
            self.instance.is_staff = False
            self.instance.is_superuser = False
        return tipo_usuario

    def clean_status(self):
        """Define se o usuário está ativo"""
        status = self.cleaned_data.get('status')
        self.instance.is_active = (status == 'ativo')
        return status

    def save(self, commit=True):
        """Salva o usuário com senha e relações many-to-many"""
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        if password:  # Define senha apenas se preenchida
            user.set_password(password)

        if commit:
            user.save()
            self.save_m2m()  # Salva relações many-to-many (páginas)
        return user


class ClienteForm(forms.ModelForm):
    """Form para cadastro e edição de clientes/tenants"""
    
    subdominio = forms.CharField(
        max_length=50, 
        help_text="Será usado como: subdominio.seudominio.com.br"
    )
    email_master = forms.EmailField(help_text="Email do usuário master")
    senha_master = forms.CharField(
        widget=forms.PasswordInput, 
        help_text="Senha do usuário master"
    )
    data_inicio_assinatura = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    data_validade_assinatura = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Cliente
        fields = [
            'nome', 'cor_primaria', 'cor_secundaria', 'data_inicio_assinatura', 
            'data_validade_assinatura', 'observacoes', 'logo', 'qtd_usuarios'
        ]
        widgets = {
            'data_inicio_assinatura': forms.DateInput(attrs={'type': 'date'}),
            'data_validade_assinatura': forms.DateInput(attrs={'type': 'date'}),
            'cor_primaria': forms.TextInput(attrs={'type': 'color'}),
            'cor_secundaria': forms.TextInput(attrs={'type': 'color'}),
        }


# Sistema de questões
class QuestaoForm(forms.ModelForm):
    """Form para criação e edição de questões"""
    
    class Meta:
        model = Questao
        fields = ['titulo', 'materia', 'ano_escolar', 'tipo']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enunciado da Questão'
            }),
            'materia': forms.Select(attrs={'class': 'form-control'}),
            'ano_escolar': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'titulo': 'Enunciado da questão',
            'materia': 'Matéria',
            'ano_escolar': 'Série',
            'tipo': 'Tipo de questão',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Agrupar anos escolares por grupo de ensino para melhor organização
        anos_por_grupo = {}
        for ano in AnoEscolar.objects.select_related('grupo_ensino').all():
            grupo_nome = ano.grupo_ensino.nome
            if grupo_nome not in anos_por_grupo:
                anos_por_grupo[grupo_nome] = []
            anos_por_grupo[grupo_nome].append((ano.id, ano.nome))
        
        # Criar opções agrupadas para o select
        choices = []
        for grupo_nome, anos in anos_por_grupo.items():
            group_options = [(id, nome) for id, nome in anos]
            choices.append((grupo_nome, group_options))
        
        self.fields['ano_escolar'].choices = choices


class ImagemQuestaoForm(forms.ModelForm):
    """Form para anexar imagens às questões"""
    
    class Meta:
        model = ImagemQuestao
        fields = ['imagem', 'legenda']
        widgets = {
            'legenda': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Legenda'
            }),
            'imagem': forms.FileInput(attrs={'class': 'form-control-file'}),
        }


# FormSet para múltiplas imagens por questão
ImagemQuestaoFormSet = forms.inlineformset_factory(
    Questao, 
    ImagemQuestao,
    form=ImagemQuestaoForm,
    extra=1,  # Inicia com 1 formulário vazio
    can_delete=True  # Permite exclusão de imagens
)


class AlternativaMultiplaEscolhaForm(forms.ModelForm):
    """Form para alternativas de questões de múltipla escolha"""
    
    class Meta:
        model = AlternativaMultiplaEscolha
        fields = ['texto', 'correta', 'ordem']
        widgets = {
            'texto': forms.TextInput(attrs={'class': 'form-control'}),
            'correta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ordem': forms.HiddenInput(),
        }


class FraseVerdadeiroFalsoForm(forms.ModelForm):
    """Form para frases de questões verdadeiro/falso"""
    
    class Meta:
        model = FraseVerdadeiroFalso
        fields = ['texto', 'verdadeira', 'ordem']
        widgets = {
            'texto': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Texto da Frase'
            }),
            'verdadeira': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ordem': forms.HiddenInput(),
        }


class ConfiguracaoSistemaForm(forms.ModelForm):
    """Form para configurações globais do sistema"""
    
    class Meta:
        model = ConfiguracaoSistema
        fields = ['imagem_home_1', 'imagem_home_2', 'observacoes', 'tempo_maximo_inatividade']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'tempo_maximo_inatividade': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 1, 
                'max': 1440  # Máximo de 24h em minutos
            }),
        }