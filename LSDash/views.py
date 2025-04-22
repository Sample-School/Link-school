from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
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

#Imports Locais
from .forms import UserLoginForm, CollabManageForm, ClienteForm
from .models import UserModel, Pagina, Cliente, Dominio, UsuarioMaster
from django.shortcuts import render, redirect, get_object_or_404


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


class EditarClienteView(View):
    template_name = 'ClienteEdit.html'

    def get(self, request):
        cliente_id = request.GET.get('cliente_id')
        form = ClienteForm()
        cliente_selecionado = None
        cliente_data = {}

        if cliente_id:
            try:
                cliente_selecionado = Cliente.objects.get(id=cliente_id)
                usuario_master = cliente_selecionado.usuario_master
                dominio = Dominio.objects.filter(tenant=cliente_selecionado).first()

                cliente_data = {
                    'nome': cliente_selecionado.nome,
                    'cor_primaria': cliente_selecionado.cor_primaria,
                    'cor_secundaria': cliente_selecionado.cor_secundaria,
                    'data_inicio_assinatura': cliente_selecionado.data_inicio_assinatura,
                    'data_validade_assinatura': cliente_selecionado.data_validade_assinatura,
                    'observacoes': cliente_selecionado.observacoes,
                    'logo': cliente_selecionado.logo,
                    'qtd_usuarios': cliente_selecionado.qtd_usuarios,
                    'responsavel': cliente_selecionado.responsavel,
                    'email_contato': cliente_selecionado.email_contato,
                    'subdominio': dominio.domain if dominio else '',
                    'email_master': usuario_master.email if usuario_master else '',
                    'senha_master': '',
                    'url_usuario': f"https://{dominio.domain}" if dominio else '',
                    'login_cliente': usuario_master.email if usuario_master else '',
                }
                form = ClienteForm(initial=cliente_data)
            except Cliente.DoesNotExist:
                messages.error(request, 'Cliente não encontrado.')

        todos_clientes = Cliente.objects.all()
        return render(request, self.template_name, {
            'form': form,
            'cliente_id': cliente_id,
            'clientes': todos_clientes,
            'cliente_selecionado': cliente_selecionado,
            'url_usuario': cliente_data.get('url_usuario', ''),
            'login_cliente': cliente_data.get('login_cliente', ''),
        })

    def post(self, request):
        cliente_id = request.POST.get('cliente_id')
        if not cliente_id:
            messages.error(request, 'ID do cliente não enviado.')
            return redirect('EditarCliente')

        cliente = get_object_or_404(Cliente, id=cliente_id)
        form = ClienteForm(request.POST, request.FILES, instance=cliente)

        if form.is_valid():
            cliente = form.save()

            subdominio = form.cleaned_data.get('subdominio')
            email_master = form.cleaned_data.get('email_master')
            senha_master = form.cleaned_data.get('senha_master')

            dominio, _ = Dominio.objects.get_or_create(tenant=cliente)
            dominio.domain = subdominio
            dominio.is_primary = True
            dominio.save()

            usuario_master = cliente.usuario_master
            if usuario_master:
                usuario_master.email = email_master
                if senha_master:
                    usuario_master.set_password(senha_master)
                usuario_master.save()

            messages.success(request, 'Cliente atualizado com sucesso.')
            return redirect(f"{reverse('EditarCliente')}?cliente_id={cliente.id}")

        todos_clientes = Cliente.objects.all()
        return render(request, self.template_name, {
            'form': form,
            'cliente_id': cliente_id,
            'clientes': todos_clientes,
            'cliente_selecionado': cliente,
        })