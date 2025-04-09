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
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .forms import UserLoginForm
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.db import IntegrityError

#Imports Locais
from .forms import UserLoginForm, CollabManageForm
from .models import UserModel


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.GET.get('user_id') or kwargs.get('user_id')
        logged_user = self.request.user

        if user_id:
            try:
                selected_user = UserModel.objects.get(user_id=user_id)
                context['selected_user'] = selected_user  # Mudado de 'user' para 'selected_user'
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
        context['logged_user'] = logged_user  # Adicionando o usuário logado ao contexto

        return context

    def post(self, request, *args, **kwargs):
        user_id = request.GET.get('user_id') or kwargs.get('user_id')

        if user_id:
            try:
                selected_user = UserModel.objects.get(user_id=user_id)  # Mudado de user para selected_user
                old_password = selected_user.password
                
                form = CollabManageForm(request.POST, instance=selected_user)
                
                if form.is_valid():
                    updated_user = form.save(commit=False)
                    updated_user.password = old_password
                    updated_user.save()
                    form.save_m2m()
                    
                    messages.success(request, "Usuário atualizado com sucesso!", extra_tags="user_edit")
                    return redirect(f"{reverse('AT-A-EU-001')}?user_id={user_id}")
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
        
        
        
        
        context = {
            
            
            
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
            
            
            context = {
                
                'form_data': request.POST,
                'errors': errors,
            }
            return render(request, 'userRegister.html', context)

        try:
            user = UserModel.objects.create_user(
                username=username,
                fullname=fullname,
                email=email,
                password=password,
                is_active=is_active,
                observacoes=observacoes
            )

            if tipo_usuario == 'administrador':
                user.is_staff = True
                user.is_superuser = True
            else:
                user.is_staff = False
                user.is_superuser = False

            
            user.save()

            messages.success(request, "Usuário registrado com sucesso.")
            return redirect('AT-A-CU-001')

        except IntegrityError as e:
            # Tratamento específico para erros de integridade
            if 'username' in str(e).lower():
                errors['username'] = "Este nome de usuário já está em uso."
            elif 'email' in str(e).lower():
                errors['email'] = "Este e-mail já está cadastrado."
            else:
                errors['general'] = "Erro ao criar usuário. Por favor, verifique os dados informados."
            
            context = {

                'form_data': request.POST,
                'errors': errors,
            }
            return render(request, 'userRegister.html', context)
            
        except Exception as e:
            messages.error(request, f"Erro inesperado: {str(e)}")
            return redirect('AT-A-CU-001')