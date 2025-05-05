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
from django.utils import timezone
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView

from .forms import CustomPasswordResetForm
from .models import UsuarioCliente

class ClienteUserLoginView(LoginView):
    template_name = "clienteLogin.html"
    success_url = reverse_lazy('LSCliente:clientehome')
    form_class = UserLoginForm

    def get_form_kwargs(self):
        # Adiciona o request aos kwargs do formulário
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def post(self, request, *args, **kwargs):
        # Usa o método get_form_kwargs para garantir que o request seja passado
        form_kwargs = self.get_form_kwargs()
        form = self.form_class(**form_kwargs)
        
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(self.get_success_url())
        return self.form_invalid(form)

    def get_success_url(self):
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "ClienteLogin"
        context["tenant_name"] = self.request.tenant.nome if hasattr(self.request, 'tenant') else "Public"
        return context

class ClienteHomeView(TemplateView):
    template_name = 'cliente_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Home"
        # Adicionar a lista de usuários ao contexto
        from LSCliente.models import UsuarioCliente
        context["usuarios"] = UsuarioCliente.objects.all().order_by('nome')
        context["tenant_name"] = self.request.tenant.nome
        context["tenant_schema"] = self.request.tenant.schema_name
        return context

class TenantPasswordResetView(PasswordResetView):
    """
    View para reset de senha que é consciente do tenant atual.
    """
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passa o request para o formulário
        kwargs['request'] = self.request
        return kwargs

class TenantAwarePasswordResetConfirmView(View):
    """
    Uma versão completamente personalizada do PasswordResetConfirmView 
    que é consciente do sistema multi-tenant.
    """
    template_name = 'cliente_password_reset/password_reset_senha_nova_form.html'
    success_url = reverse_lazy('LSCliente:clientepassword_reset_complete')
    
    def get(self, request, *args, **kwargs):
        """
        Exibe o formulário de redefinição de senha e valida o token
        """
        # Debug
        print(f"[DEBUG] TenantAwarePasswordResetConfirmView GET chamado no tenant: {request.tenant.schema_name}")
        print(f"[DEBUG] uidb64: {kwargs.get('uidb64')}")
        print(f"[DEBUG] token: {kwargs.get('token')}")
        
        context = self._get_context_with_user(request, **kwargs)
        
        if context['validlink']:
            form = NewResetPasswordForm(user=context['user'])
            context['form'] = form
        
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        """
        Processa o formulário de redefinição de senha
        """
        # Debug
        print(f"[DEBUG] TenantAwarePasswordResetConfirmView POST chamado no tenant: {request.tenant.schema_name}")
        
        context = self._get_context_with_user(request, **kwargs)
        
        if not context['validlink']:
            return render(request, self.template_name, context)
        
        form = NewResetPasswordForm(user=context['user'], data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Sua senha foi alterada com sucesso!")
            return redirect(self.success_url)
        
        context['form'] = form
        return render(request, self.template_name, context)
    
    def _get_context_with_user(self, request, **kwargs):
        """
        Método auxiliar para obter o contexto com informações do usuário e validação do token
        """
        context = {
            'validlink': False,
            'user': None,
            'tenant': request.tenant,
            'tenant_name': request.tenant.schema_name,
        }
        
        try:
            # Decodificar o uidb64
            uid = force_str(urlsafe_base64_decode(kwargs.get('uidb64', '')))
            print(f"[DEBUG] UID decodificado: {uid}")
            
            try:
                # Obtenha o usuário do tenant atual usando UsuarioCliente
                user = UsuarioCliente.objects.get(pk=uid)
                print(f"[DEBUG] Usuário encontrado: {user.email}")
                
                # Verificar o token
                token = kwargs.get('token', '')
                if default_token_generator.check_token(user, token):
                    context['validlink'] = True
                    context['user'] = user
                    print(f"[DEBUG] Token válido para usuário {user.email}")
                else:
                    print(f"[DEBUG] Token inválido para usuário {user.email}")
            except UsuarioCliente.DoesNotExist:
                print(f"[DEBUG] Usuário com ID {uid} não encontrado no tenant {request.tenant.schema_name}")
        except (TypeError, ValueError, OverflowError) as e:
            print(f"[DEBUG] Erro ao decodificar UID: {str(e)}")
        
        return context