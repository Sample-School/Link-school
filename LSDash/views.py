from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy,  reverse
from django.contrib import messages
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from .forms import NewResetPasswordForm
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .forms import UserLoginForm
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.db import IntegrityError
from django_tenants.utils import tenant_context
from django.utils.text import slugify
from django import forms
#Imports Locais
from .forms import UserLoginForm, CollabManageForm, ClienteForm, QuestaoForm, ImagemQuestaoFormSet, AlternativaMultiplaEscolhaForm, FraseVerdadeiroFalsoForm
from .models import UserModel, Pagina, Cliente, Dominio, UsuarioMaster, Questao, ImagemQuestao, AlternativaMultiplaEscolha, FraseVerdadeiroFalso


class UserLoginView(LoginView):
    template_name = "login.html"  # Template a ser usado
    success_url = reverse_lazy('home')  # Para onde redirecionar após login com sucesso
    form_class = UserLoginForm  # Formulário de login personalizado

    def post(self, request, *args, **kwargs):
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            # Django chama o campo de "username" no form, mesmo que seja um email
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Autentica o usuário com base no email (caso seu AUTH_USER_MODEL use email como USERNAME_FIELD)
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect(self.get_success_url())  # Redireciona após login
                else:
                    form.add_error(None, "Esta conta está inativa.")
            else:
                form.add_error(None, "Email ou senha incorretos.")
        return self.form_invalid(form)

    def get_success_url(self):
        return self.success_url

    def get_context_data(self, **kwargs):
        # Adiciona variável de contexto ao template
        context = super().get_context_data(**kwargs)
        context["title"] = "Login"
        return context


# Página protegida por login
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Home"
        return context


class CollabManage(LoginRequiredMixin,  TemplateView):
    template_name = 'CollabManage.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.GET.get('user_id') or kwargs.get('user_id')
        logged_user = self.request.user

        if user_id:
            try:
                selected_user = UserModel.objects.get(user_id=user_id)
                print(f"Usuário encontrado: {selected_user.username}, ID: {selected_user.user_id}")
                context['selected_user'] = selected_user
                context['form'] = CollabManageForm(instance=selected_user)
                context['user_id'] = user_id
                context['tipo_usuario_display'] = (
                    'Administrador' if selected_user.is_staff and selected_user.is_superuser else 'Colaborador'
                )
                context['status_usuario_display'] = (
                    'Ativo' if selected_user.is_active else 'Inativo'
                )
            except UserModel.DoesNotExist:
                context['error_message'] = f"Usuário com ID {user_id} não encontrado."
                context['form'] = CollabManageForm()
        else:
            context['form'] = CollabManageForm()

        context['users'] = UserModel.objects.all()
        context['logged_user'] = logged_user
        return context
    
    def post(self, request, *args, **kwargs):
        user_id = request.GET.get('user_id') or kwargs.get('user_id')

        if user_id:
            try:
                selected_user = UserModel.objects.get(user_id=user_id)  # Mudado de user para selected_user
                old_password = selected_user.password
                
                form = CollabManageForm(request.POST,request.FILES, instance=selected_user)
                
                if form.is_valid():
                    updated_user = form.save(commit=False)
                    updated_user.password = old_password
                    updated_user.save()
                    # Salvar relações many-to-many, incluindo as páginas
                    form.save_m2m()
                    
                    messages.success(request, "Usuário atualizado com sucesso!", extra_tags="user_edit")
                    return redirect(f"{reverse('collabmanage')}?user_id={user_id}")
                else:
                    messages.error(request, "Erro no formulário. Por favor, verifique os campos." , extra_tags="user_edit")
                    return self.render_to_response(self.get_context_data(form=form, selected_user=selected_user))
            except UserModel.DoesNotExist:
                messages.error(request, f"Usuário com ID {user_id} não encontrado.", extra_tags="user_edit")
                return self.render_to_response(self.get_context_data())
        else:
            messages.error(request, "Usuário não encontrado.", extra_tags="user_edit")
            return self.render_to_response(self.get_context_data())


class CollabRegisterView(LoginRequiredMixin, View):
    def get(self, request):
        # Obter todas as páginas para o select multiple
        paginas = Pagina.objects.all()
        
        context = {
            'form': {
                'fullname': {'value': ''},
                'username': {'value': ''},
                'email': {'value': ''},
                'tipo_usuario': {'value': 'colaborador'},
                'is_active': {'value': 'True'},
                'observacoes': {'value': ''},
                'paginas': {'value': []},
                'fields': {'paginas': {'queryset': paginas}}
            }
        }
        return render(request, 'CollabRegister.html', context)

    def post(self, request):
        username = request.POST.get('username')
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        tipo_usuario = request.POST.get('tipo_usuario')
        is_active = request.POST.get('is_active') == 'True'
        observacoes = request.POST.get('observacoes', '')
        paginas_ids = request.POST.getlist('paginas')
        user_img = request.FILES.get('user_img')

        errors = {}
        UserModel = get_user_model()

        # Validação básica dos campos
        if not username:
            errors['username'] = "O campo Nome de Usuário é obrigatório."
        elif UserModel.objects.filter(username=username).exists():
            errors['username'] = "Este nome de usuário já está em uso."
            
        if not fullname:
            errors['fullname'] = "O campo Nome Completo é obrigatório."
            
        if not email:
            errors['email'] = "O campo E-mail é obrigatório."
        elif '@' not in email:
            errors['email'] = "Forneça um e-mail válido."
        elif UserModel.objects.filter(email=email).exists():
            errors['email'] = "Este e-mail já está cadastrado."
            
        if not password:
            errors['password'] = "O campo Senha é obrigatório."
        elif len(password) < 6:
            errors['password'] = "A senha deve ter pelo menos 6 caracteres."

        
        # Se houver erros, retorna o formulário com os erros
        if errors:
            # Obter novamente todas as páginas para o formulário
            paginas = Pagina.objects.all()
            
            context = {
                'form': {
                    'fullname': {'value': fullname},
                    'username': {'value': username},
                    'email': {'value': email},
                    'tipo_usuario': {'value': tipo_usuario},
                    'is_active': {'value': is_active},
                    'observacoes': {'value': observacoes},
                    'paginas': {'value': paginas_ids},
                    'fields': {'paginas': {'queryset': paginas}}
                },
                'errors': errors,
            }
            return render(request, 'CollabRegister.html', context)

        try:
            user = UserModel.objects.create_user(
                username=username,
                fullname=fullname,
                email=email,
                password=password,
                is_active=is_active,
                observacoes=observacoes,
                user_img=user_img
            )

            if tipo_usuario == 'administrador':
                user.is_staff = True
                user.is_superuser = True
            else:
                user.is_staff = False
                user.is_superuser = False

            
            user.save()
            
            # Vincular páginas ao usuário
            if paginas_ids:
                paginas = Pagina.objects.filter(id__in=paginas_ids)
                user.paginas.set(paginas)
                
            messages.success(request, "Usuário registrado com sucesso.")
            return redirect('collabregister')

        except IntegrityError as e:
            # Tratamento específico para erros de integridade
            if 'username' in str(e).lower():
                errors['username'] = "Este nome de usuário já está em uso."
            elif 'email' in str(e).lower():
                errors['email'] = "Este e-mail já está cadastrado."
            else:
                errors['general'] = "Erro ao criar usuário. Por favor, verifique os dados informados."
            
            # Obter novamente todas as páginas para o formulário
            paginas = Pagina.objects.all()
            
            context = {
                'form': {
                    'fullname': {'value': fullname},
                    'username': {'value': username},
                    'email': {'value': email},
                    'tipo_usuario': {'value': tipo_usuario},
                    'is_active': {'value': is_active},
                    'observacoes': {'value': observacoes},
                    'paginas': {'value': paginas_ids},
                    'fields': {'paginas': {'queryset': paginas}}
                },
                'errors': errors,
            }
            return render(request, 'CollabRegister.html', context)
            
        except Exception as e:
            messages.error(request, f"Erro inesperado: {str(e)}")
            return redirect('collabregister')

def custom_logout_view(request):
    logout(request)
    return redirect('login')


class CadastroClienteView(LoginRequiredMixin, View):
    template_name = 'ClienteRegister.html'
    
    def get(self, request):
        form = ClienteForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = ClienteForm(request.POST, request.FILES)
        
        if form.is_valid():
            dados = form.cleaned_data
            
            try:
                # Criar o cliente com o usuário master usando nosso manager personalizado
                cliente = Cliente.objects.create_cliente_with_master(
                    nome=dados['nome'],
                    email_master=dados['email_master'],
                    password_master=dados['senha_master'],
                    cor_primaria=dados['cor_primaria'],
                    cor_secundaria=dados['cor_secundaria'],
                    data_inicio_assinatura=dados['data_inicio_assinatura'],
                    data_validade_assinatura=dados['data_validade_assinatura'],
                    observacoes=dados['observacoes'],
                    logo=dados.get('logo'),
                    qtd_usuarios=dados['qtd_usuarios'],
                    responsavel=dados['responsavel'],
                    email_contato=dados['email_contato'],
                    schema_name = slugify(dados['nome'])
                )
                
                # Criar o domínio
                subdominio = dados['subdominio']
                dominio_base = 'seudominio.com.br'
                dominio_completo = f"{subdominio}.{dominio_base}"
                
                dominio = Dominio()
                dominio.domain = dominio_completo
                dominio.tenant = cliente
                dominio.is_primary = True
                dominio.save()
                
                # Sincronizar usuário master dentro do tenant
                with tenant_context(cliente):
                    from LSCliente.models import UsuarioCliente
                    
                    # Criar um usuário equivalente dentro do tenant
                    usuario_tenant = UsuarioCliente.objects.create_superuser(
                        email=dados['email_master'],
                        password=dados['senha_master'],
                        nome=dados['responsavel'],
                    )
                
                messages.success(request, f"Cliente {cliente.nome} cadastrado com sucesso!")
                return redirect('lista_clientes')
                
            except Exception as e:
                messages.error(request, f"Erro ao cadastrar cliente: {str(e)}")
        
        return render(request, self.template_name, {'form': form})
    

AlternativaFormSet = forms.inlineformset_factory(
    Questao, 
    AlternativaMultiplaEscolha,
    form=AlternativaMultiplaEscolhaForm,
    extra=5,  # 5 alternativas para múltipla escolha
    max_num=5,
    can_delete=True
)

FraseVFFormSet = forms.inlineformset_factory(
    Questao, 
    FraseVerdadeiroFalso,
    form=FraseVerdadeiroFalsoForm,
    extra=4,  # 4 frases para verdadeiro/falso
    max_num=4,
    can_delete=True
)

class QuestaoManageView(LoginRequiredMixin, View):
    template_name = 'questionRegister.html'
    
    def get(self, request):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)
    
    def post(self, request):
        questao_id = request.POST.get('questao_id')
        
        # Se tiver ID, estamos editando uma questão existente
        if questao_id:
            return self.update_questao(request, questao_id)
        else:
            return self.create_questao(request)
    
    def get_context_data(self, request):
        context = {}
        
        # Busca por ID de questão
        questao_id = request.GET.get('questao_id')
        if questao_id:
            try:
                questao = Questao.objects.get(id=questao_id)
                context['questao'] = questao
                context['questao_form'] = QuestaoForm(instance=questao)
                context['imagem_formset'] = ImagemQuestaoFormSet(instance=questao)
                
                # Adicionar formsets específicos baseados no tipo da questão
                if questao.tipo == 'multipla':
                    context['alternativa_formset'] = AlternativaFormSet(instance=questao)
                elif questao.tipo == 'vf':
                    context['frase_vf_formset'] = FraseVFFormSet(instance=questao)
                
            except Questao.DoesNotExist:
                messages.error(request, f"Questão com ID {questao_id} não encontrada.")
                context['questao_form'] = QuestaoForm()
                context['imagem_formset'] = ImagemQuestaoFormSet()
                context['alternativa_formset'] = AlternativaFormSet()
                context['frase_vf_formset'] = FraseVFFormSet()
        else:
            context['questao_form'] = QuestaoForm()
            context['imagem_formset'] = ImagemQuestaoFormSet()
            context['alternativa_formset'] = AlternativaFormSet()
            context['frase_vf_formset'] = FraseVFFormSet()
        
        # Lista de questões para seleção
        context['questoes'] = Questao.objects.select_related('materia', 'ano_escolar', 'criado_por').all().order_by('-data_criacao')[:50]  # Limitando a 50 para performance
        
        return context
    
    def create_questao(self, request):
        questao_form = QuestaoForm(request.POST)
        imagem_formset = ImagemQuestaoFormSet(request.POST, request.FILES)
        
        # FormSets serão processados conforme o tipo de questão
        alternativa_formset = None
        frase_vf_formset = None
        
        if questao_form.is_valid():
            # Salvar a questão com o usuário atual
            questao = questao_form.save(commit=False)
            questao.criado_por = request.user
            questao.save()
            
            # Validar e salvar o formset de imagens
            imagem_formset = ImagemQuestaoFormSet(request.POST, request.FILES, instance=questao)
            if imagem_formset.is_valid():
                imagens = imagem_formset.save(commit=False)
                for imagem in imagens:
                    imagem.questao = questao
                    imagem.save()
                
                for obj in imagem_formset.deleted_objects:
                    obj.delete()
            
            # Processar formsets específicos com base no tipo da questão
            is_specific_formset_valid = True
            
            if questao.tipo == 'multipla':
                alternativa_formset = AlternativaFormSet(request.POST, request.FILES, instance=questao)
                if alternativa_formset.is_valid():
                    alternativas = alternativa_formset.save(commit=False)
                    for i, alternativa in enumerate(alternativas):
                        alternativa.questao = questao
                        alternativa.ordem = i
                        alternativa.save()
                    
                    for obj in alternativa_formset.deleted_objects:
                        obj.delete()
                else:
                    is_specific_formset_valid = False
            
            elif questao.tipo == 'vf':
                frase_vf_formset = FraseVFFormSet(request.POST, request.FILES, instance=questao)
                if frase_vf_formset.is_valid():
                    frases = frase_vf_formset.save(commit=False)
                    for i, frase in enumerate(frases):
                        frase.questao = questao
                        frase.ordem = i
                        frase.save()
                    
                    for obj in frase_vf_formset.deleted_objects:
                        obj.delete()
                else:
                    is_specific_formset_valid = False
            
            if imagem_formset.is_valid() and is_specific_formset_valid:
                messages.success(request, "Questão cadastrada com sucesso!")
                return redirect('questao_manage')
        
        # Se chegou aqui, houve erro em algum formulário
        messages.error(request, "Erro ao cadastrar questão. Verifique os dados informados.")
        context = {
            'questao_form': questao_form,
            'imagem_formset': imagem_formset,
            'questoes': Questao.objects.all().order_by('-data_criacao')[:50]
        }
        
        # Adicionar formsets específicos ao contexto, se necessário
        if questao_form.is_valid():
            tipo_questao = questao_form.cleaned_data['tipo']
            if tipo_questao == 'multipla':
                context['alternativa_formset'] = alternativa_formset or AlternativaFormSet(request.POST)
            elif tipo_questao == 'vf':
                context['frase_vf_formset'] = frase_vf_formset or FraseVFFormSet(request.POST)
        else:
            context['alternativa_formset'] = AlternativaFormSet()
            context['frase_vf_formset'] = FraseVFFormSet()
        
        return render(request, self.template_name, context)
    
    def update_questao(self, request, questao_id):
        questao = get_object_or_404(Questao, id=questao_id)
        questao_form = QuestaoForm(request.POST, instance=questao)
        imagem_formset = ImagemQuestaoFormSet(request.POST, request.FILES, instance=questao)
        
        # FormSets serão processados conforme o tipo de questão
        alternativa_formset = None
        frase_vf_formset = None
        
        if questao_form.is_valid() and imagem_formset.is_valid():
            # Salvar a questão principal
            questao = questao_form.save()
            
            # Salvar o formset de imagens
            imagens = imagem_formset.save(commit=False)
            for imagem in imagens:
                imagem.questao = questao
                imagem.save()
            
            for obj in imagem_formset.deleted_objects:
                obj.delete()
            
            # Processar formsets específicos com base no tipo da questão
            is_specific_formset_valid = True
            
            if questao.tipo == 'multipla':
                alternativa_formset = AlternativaFormSet(request.POST, request.FILES, instance=questao)
                if alternativa_formset.is_valid():
                    alternativas = alternativa_formset.save(commit=False)
                    for i, alternativa in enumerate(alternativas):
                        alternativa.questao = questao
                        alternativa.ordem = i
                        alternativa.save()
                    
                    for obj in alternativa_formset.deleted_objects:
                        obj.delete()
                else:
                    is_specific_formset_valid = False
            
            elif questao.tipo == 'vf':
                frase_vf_formset = FraseVFFormSet(request.POST, request.FILES, instance=questao)
                if frase_vf_formset.is_valid():
                    frases = frase_vf_formset.save(commit=False)
                    for i, frase in enumerate(frases):
                        frase.questao = questao
                        frase.ordem = i
                        frase.save()
                    
                    for obj in frase_vf_formset.deleted_objects:
                        obj.delete()
                else:
                    is_specific_formset_valid = False
            
            if is_specific_formset_valid:
                messages.success(request, "Questão atualizada com sucesso!")
                return redirect(f"questao_manage?questao_id={questao_id}")
        
        # Se chegou aqui, houve erro em algum formulário
        messages.error(request, "Erro ao atualizar questão. Verifique os dados informados.")
        context = {
            'questao': questao,
            'questao_form': questao_form,
            'imagem_formset': imagem_formset,
            'questoes': Questao.objects.all().order_by('-data_criacao')[:50]
        }
        
        # Adicionar formsets específicos ao contexto, se necessário
        if questao.tipo == 'multipla':
            context['alternativa_formset'] = alternativa_formset or AlternativaFormSet(instance=questao)
        elif questao.tipo == 'vf':
            context['frase_vf_formset'] = frase_vf_formset or FraseVFFormSet(instance=questao)
        
        return render(request, self.template_name, context)
