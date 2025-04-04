from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,  # Adicionei para customização
)
from django.urls import reverse_lazy
from .forms import UserLoginForm
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class UserLoginView(LoginView):
    template_name = "registration/login.html"
    success_url = reverse_lazy('home')  # URL para redirecionar após login
    form_class = UserLoginForm

    def get_context_data(self, **kwargs):
        """Adiciona contexto extra (opcional)"""
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Login"  # Exemplo: pode ser usado no base.html
        return context

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user': self.request.user,
            'page_title': "Dashboard"  # Título dinâmico
        })
        return context


class CustomPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"  # Seu template customizado
    email_template_name = 'LSDash/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')