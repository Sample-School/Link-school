from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django import forms

#imports locais
from .models import UserModel, Pagina, Cliente, GrupoEnsino, AnoEscolar, Materia, Questao, ImagemQuestao, AlternativaMultiplaEscolha, FraseVerdadeiroFalso
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


class ClienteForm(forms.ModelForm):
    subdominio = forms.CharField(max_length=50, help_text="Será usado como: subdominio.seudominio.com.br")
    email_master = forms.EmailField(help_text="Email do usuário master")
    senha_master = forms.CharField(widget=forms.PasswordInput, help_text="Senha do usuário master")
    responsavel = forms.CharField(max_length=100, help_text="Nome do responsável/administrador")
    email_contato = forms.EmailField(help_text="Email de contato da instituição")
    

    class Meta:
        model = Cliente
        fields = [
            'nome',
            'cor_primaria',
            'cor_secundaria',
            'data_inicio_assinatura',
            'data_validade_assinatura',
            'observacoes',
            'logo',
            'qtd_usuarios',
            'subdominio',
            'email_master',
            'senha_master',
            'responsavel',
            'email_contato',

        ]
        widgets = {
            'data_inicio_assinatura': forms.DateInput(attrs={'type': 'date'}),
            'data_validade_assinatura': forms.DateInput(attrs={'type': 'date'}),
            'cor_primaria': forms.TextInput(attrs={'type': 'color'}),
            'cor_secundaria': forms.TextInput(attrs={'type': 'color'}),
        }

class QuestaoForm(forms.ModelForm):
    class Meta:
        model = Questao
        fields = ['titulo', 'materia', 'ano_escolar', 'tipo']
        widgets = {
            'titulo': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'materia': forms.Select(attrs={'class': 'form-control'}),
            'ano_escolar': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.RadioSelect(),
        }
        labels = {
            'titulo': 'Enunciado da questão',
            'materia': 'Matéria',
            'ano_escolar': 'Ano Escolar',
            'tipo': 'Tipo de questão',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Agrupar anos escolares por grupo de ensino para o select
        anos_por_grupo = {}
        for ano in AnoEscolar.objects.select_related('grupo_ensino').all():
            grupo_nome = ano.grupo_ensino.nome
            if grupo_nome not in anos_por_grupo:
                anos_por_grupo[grupo_nome] = []
            anos_por_grupo[grupo_nome].append((ano.id, ano.nome))
        
        # Criar as opções do campo com grupos
        choices = []
        for grupo_nome, anos in anos_por_grupo.items():
            group_options = [(id, nome) for id, nome in anos]
            choices.append((grupo_nome, group_options))
        
        # Atualizar o campo ano_escolar com as opções agrupadas
        self.fields['ano_escolar'].choices = choices

class ImagemQuestaoForm(forms.ModelForm):
    class Meta:
        model = ImagemQuestao
        fields = ['imagem', 'legenda']
        widgets = {
            'legenda': forms.TextInput(attrs={'class': 'form-control'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

# FormSet para múltiplas imagens
ImagemQuestaoFormSet = forms.inlineformset_factory(
    Questao, 
    ImagemQuestao,
    form=ImagemQuestaoForm,
    extra=1,  # Começa com 1 formulário vazio
    can_delete=True  # Permite excluir imagens
)


class AlternativaMultiplaEscolhaForm(forms.ModelForm):
    class Meta:
        model = AlternativaMultiplaEscolha
        fields = ['texto', 'correta', 'ordem']
        widgets = {
            'texto': forms.TextInput(attrs={'class': 'form-control'}),
            'correta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ordem': forms.HiddenInput(),
        }

class FraseVerdadeiroFalsoForm(forms.ModelForm):
    class Meta:
        model = FraseVerdadeiroFalso
        fields = ['texto', 'verdadeira', 'ordem']
        widgets = {
            'texto': forms.TextInput(attrs={'class': 'form-control'}),
            'verdadeira': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ordem': forms.HiddenInput(),
        }
